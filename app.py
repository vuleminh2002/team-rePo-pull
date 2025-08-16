from flask import Flask, jsonify
import subprocess
import os
import shutil
import firebase_admin
from firebase_admin import credentials, db

# Initialize Flask app
app = Flask(__name__)

# Initialize Firebase Admin SDK for Realtime Database
cred = credentials.Certificate('ai-in-music-firebase-adminsdk-f44ex-127e3c135a.json')  
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://ai-in-music-default-rtdb.firebaseio.com/'  
})

@app.route('/')
def home():
    return 'Welcome'

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/pull_and_transfer', methods=['GET'])
def pull_and_transfer():
    # Correctly accessing the root reference of the Realtime Database
    ref = db.reference('/16O4emZAUibrcYEoLiwYb0bdLCYs-Y-nar3XhqtU3V4M/page1')  # Adjust the path based on your structure
    data = ref.get()  # Fetch all data under this path

    # Check if data is None
    if data is None:
        print("No data found at the specified path.")
        return jsonify({"error": "No data found at the specified path."}), 404

    results = []

    # Check if data is a list or a dictionary and iterate accordingly
    if isinstance(data, list):
        # If the data is a list, iterate through the list
        for team in data:
            if not isinstance(team, dict):
                continue  # Skip if the element is not a dictionary
            process_team(team, results)
    elif isinstance(data, dict):
        # If the data is a dictionary, iterate through the items
        for record_id, team in data.items():
            process_team(team, results)
    else:
        print("Unexpected data structure.")
        return jsonify({"error": "Unexpected data structure."}), 400

    return jsonify(results)

def process_team(team, results):
    """Processes a single team's data."""
    team_name = team.get('name_of_the_team', 'Unknown Team')
    repo_url = team.get('github_repo')
    base_local_path = team.get('local_path')

    # Create a unique subdirectory for each team's code
    local_path = os.path.join(base_local_path, team_name)

    # Debug prints to verify the data
    print(f"Processing {team_name}:")
    print(f"Repository URL: {repo_url}")
    print(f"Local Path: {local_path}")

    # Verify if the paths are valid and accessible
    if not repo_url or not local_path:
        results.append({team_name: "Missing repository URL or local path"})
        return

    # Ensure the local directory exists
    try:
        os.makedirs(local_path, exist_ok=True)
    except Exception as e:
        print(f"Error creating directory {local_path}: {e}")
        results.append({team_name: f"Error creating directory: {e}"})
        return

    def is_valid_git_repo(path):
        """Check if a given directory is a valid Git repository."""
        try:
            subprocess.run(["git", "-C", path, "rev-parse", "--is-inside-work-tree"],
                           check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def get_current_remote_url(path):
        """Get the current remote URL of the git repository."""
        try:
            result = subprocess.run(
                ["git", "-C", path, "config", "--get", "remote.origin.url"],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def fetch_tags(path):
        """Fetch tags from the remote repository and prune deleted tags."""
        try:
               # Fetch all tags from the remote and remove local tags that no longer exist on the remote
            subprocess.run(["git", "-C", path, "fetch", "--tags", "--prune"], 
                           check=True, capture_output=True, text=True)
            # Explicitly remove stale local tags that are no longer on the remote
            subprocess.run(["git", "-C", path, "fetch", "--prune", "origin", "+refs/tags/*:refs/tags/*"],
                           check=True, capture_output=True, text=True)
            print(f"Fetched and pruned tags for {path}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to fetch and prune tags: {e.stderr}")


    def has_any_tag(path):
        """Check if the repository has any tags."""
        fetch_tags(path)  # Ensure tags are fetched before checking
        try:
            result = subprocess.run(
                ["git", "-C", path, "tag"],
                capture_output=True, text=True, check=True
            )
            # Check if there is any tag
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False

    # Check if the directory is a valid Git repository
    try:
        if is_valid_git_repo(local_path):
            # Check if any tag exists in the local repo
            if has_any_tag(local_path):
                print(f"Repository {team_name} has tags. Skipping pull/clone operation.")
                results.append({team_name: "Skipped due to the presence of tags"})
                return

            current_remote_url = get_current_remote_url(local_path)
            # Compare the current URL with the new URL from the database
            if current_remote_url != repo_url:
                print(f"Remote URL has changed for {team_name}. Cleaning up and re-cloning...")
                shutil.rmtree(local_path)  # Remove the old repository
                os.makedirs(local_path, exist_ok=True)  # Recreate the directory

                # Clone the new repository
                print(f"Cloning new repository for {team_name} into {local_path}...")
                subprocess.run(["git", "clone", repo_url, local_path], check=True)
            else:
                # If it's the same URL, pull the latest changes
                print(f"Pulling latest code for {team_name}...")
                subprocess.run(["git", "-C", local_path, "pull", "origin", "main"], check=True)
        else:
            # If not a valid repo, clean up and prepare to clone
            print(f"{local_path} is not a valid Git repository. Cleaning up and re-cloning...")
            shutil.rmtree(local_path)  # Remove the invalid directory
            os.makedirs(local_path, exist_ok=True)  # Recreate the directory

            # Clone the repository into the team's subdirectory
            print(f"Cloning repository for {team_name} into {local_path}...")
            subprocess.run(["git", "clone", repo_url, local_path], check=True)

        results.append({team_name: "Success"})
    except subprocess.CalledProcessError as e:
        print(f"Error processing {team_name}: {e.stderr}")
        results.append({team_name: f"Error: {e.stderr}"})
    except Exception as e:
        print(f"Unexpected error: {e}")
        results.append({team_name: f"Unexpected error: {e}"})

if __name__ == '__main__':
    app.run(debug=True)

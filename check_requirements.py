import sys
import pkg_resources

def check_requirements(requirements_path='requirements.txt'):
    """
    Checks if the requirements in the given file are satisfied by the installed packages.
    Returns 0 if all satisfied, 1 otherwise.
    """
    requirements = []
    encodings = ['utf-8', 'utf-16', 'latin-1']
    
    for enc in encodings:
        try:
            with open(requirements_path, 'r', encoding=enc) as f:
                # Filter out comments and empty lines
                requirements = [
                    line.strip() for line in f 
                    if line.strip() and not line.strip().startswith('#')
                ]
            break # Success
        except UnicodeError:
            continue
        except FileNotFoundError:
             print(f"Error: {requirements_path} not found.")
             return 1
    
    if not requirements and not encodings: # Should catch if all fail or file empty
         print("Failed to read requirements.txt with supported encodings.")
         return 1

    try:
        # This will raise DistributionNotFound or VersionConflict if mismatch
        pkg_resources.require(requirements)
        return 0
        
    except FileNotFoundError:
        print(f"Error: {requirements_path} not found.")
        return 1
    except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict) as e:
        # print(f"Requirement check: {e}") # Optional: verify what's missing
        return 1
    except Exception as e:
        print(f"Unexpected error checking requirements: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(check_requirements())

import os
import subprocess
from pathlib import Path


def main():
    """
    Run the Merck Veterinary Manual spider to fetch subsections for each main section.
    This script first checks if the initial sections have been crawled,
    then runs the spider in subsection mode.
    """
    sections_path = os.path.join("merck", "merck_sections.json")
    if not os.path.exists(sections_path):
        print(
            "Error: merck_sections.json not found. Please run 'scrapy crawl merckvetmanual' first."
        )
        return
    print("sections_path: ", sections_path)
    
    # Create section_data directory if it doesn't exist
    output_dir = os.path.join("merck", "section_data")
    Path(output_dir).mkdir(exist_ok=True)

    print("Starting subsection crawler...")
    
    # Change directory to merck folder and run scrapy command in debug mode
    current_dir = os.getcwd()
    os.chdir("merck")
    
    try:
        # Run with LOG_LEVEL=DEBUG to see detailed output
        result = subprocess.run(
            ["scrapy", "crawl", "merckvetmanual", "-a", "scrape_subsections=true", "--set", "LOG_LEVEL=DEBUG"],
            text=True,
            capture_output=True
        )
        
        print("Crawler output (summary):")
        # Extract key parts from the output
        output_lines = result.stdout.split('\n')
        for line in output_lines:
            if "Found main subsection:" in line or "Found subsection:" in line or "Method" in line:
                print(line)
        
        # Change back to original directory
        os.chdir(current_dir)
        
        if result.returncode == 0:
            print("\nSuccessfully completed subsection crawling!")
            
            # Count the number of JSON files created
            json_files = list(Path(output_dir).glob("*.json"))
            print(f"Created {len(json_files)} subsection JSON files in {output_dir}")
            
            # Check contents of a sample file
            if json_files:
                sample_file = json_files[0]
                print(f"\nSample content from {sample_file}:")
                with open(sample_file, 'r') as f:
                    print(f.read()[:500] + "..." if os.path.getsize(sample_file) > 500 else f.read())
            
            if len(json_files) == 0:
                print("\nIssue detected: No JSON files were created.")
                print("Error output:")
                print(result.stderr)
        else:
            print("Error running the crawler:")
            print(result.stderr)
    except Exception as e:
        print(f"Exception occurred: {e}")
        os.chdir(current_dir)


if __name__ == "__main__":
    main()

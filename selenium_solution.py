#!/usr/bin/env python3
"""
Merck Veterinary Manual Subsection Crawler

This script uses Selenium to navigate to each section URL in the Merck Veterinary Manual,
renders the JavaScript-loaded content, and extracts all subsections.
Each section's subsections are saved to a separate JSON file.

Usage:
    python selenium_solution.py [--test]

Options:
    --test  Run only on the Circulatory System section as a test

Requirements:
    - selenium
    - webdriver-manager

Install with:
    pip install selenium webdriver-manager
"""

import os
import json
import re
import time
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def extract_subsections_with_selenium(url, section_title):
    """
    Extract subsections from a Merck Veterinary Manual section page using Selenium to render JavaScript
    """
    print(f"Extracting subsections for {section_title} from {url}")
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Set up the driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # Navigate to the URL
        driver.get(url)
        
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Give a bit more time for JavaScript to execute
        time.sleep(5)
        
        # Get the section path from the URL
        section_path = url.split("merckvetmanual.com")[1]
        base_url = "https://www.merckvetmanual.com"
        
        # Extract subsections
        subsections = []
        
        # Find all links in the page
        links = driver.find_elements(By.TAG_NAME, "a")
        
        for link in links:
            try:
                href = link.get_attribute("href")
                text = link.text.strip()
                
                # Filter links: they should be internal, contain the section path, 
                # and not be the same as the section URL
                if (href and text and len(text) > 3 and 
                    href.startswith(base_url) and 
                    section_path in href and 
                    href != url and
                    not any(x in text.lower() for x in ['veterinary', 'pet owners', 'resources', 'quizzes', 'about', 'contact'])):
                    
                    # Check URL structure for subsections (e.g., /circulatory-system/anemia)
                    relative_path = href.replace(base_url, "")
                    parts = relative_path.strip('/').split('/')
                    
                    if len(parts) > 1 and section_path.strip('/') == parts[0]:
                        subsections.append({
                            "title": text,
                            "url": href
                        })
                        print(f"Found subsection: {text}")
            except Exception as e:
                print(f"Error processing link: {e}")
                continue
        
        # Save the page source for debugging
        with open(f"{section_title.replace(' ', '_')}_selenium_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        
        # Remove duplicates
        unique_subsections = []
        seen_urls = set()
        
        for item in subsections:
            if item['url'] not in seen_urls:
                unique_subsections.append(item)
                seen_urls.add(item['url'])
        
        return unique_subsections
    
    except Exception as e:
        print(f"Error: {e}")
        return []
    
    finally:
        # Clean up
        driver.quit()

def main():
    # Check for --test argument
    test_mode = "--test" in sys.argv
    
    # Read the clean sections file
    sections_path = os.path.join("merck", "clean_sections.json")
    
    if not os.path.exists(sections_path):
        print(f"Error: {sections_path} not found")
        return
    
    try:
        with open(sections_path, 'r') as f:
            sections = json.load(f)
        
        # Create output directory
        output_dir = os.path.join("merck", "subsections")
        Path(output_dir).mkdir(exist_ok=True)
        
        # Print status message
        if test_mode:
            print("Running in TEST mode - only processing Circulatory System")
        else:
            print(f"Preparing to extract subsections for {len(sections)} sections")
        
        # Track progress
        processed = 0
        successful = 0
        
        # In test mode, only process the Circulatory System section
        if test_mode:
            circulatory_section = next((s for s in sections if s["title"] == "Circulatory System"), None)
            if circulatory_section:
                sections = [circulatory_section]
            else:
                print("Error: Circulatory System section not found")
                return
        
        # Process all sections
        total_sections = len(sections)
        for i, section in enumerate(sections, 1):
            title = section.get("title")
            url = section.get("url")
            
            if not title or not url:
                continue
            
            print(f"\n[{i}/{total_sections}] Processing: {title}")
            
            # Extract subsections
            subsections = extract_subsections_with_selenium(url, title)
            processed += 1
            
            if subsections:
                # Save to JSON file
                safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
                output_path = os.path.join(output_dir, f"{safe_title}.json")
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(subsections, f, indent=2, ensure_ascii=False)
                
                print(f"✓ Saved {len(subsections)} subsections to {output_path}")
                successful += 1
            else:
                print(f"✗ No subsections found for {title}")
            
            # Be respectful with rate limiting (except for the last item)
            if i < total_sections:
                print("Waiting 2 seconds before next request...")
                time.sleep(2)
        
        # Print summary
        print(f"\n=== Summary ===")
        print(f"Processed: {processed}/{total_sections} sections")
        print(f"Successful: {successful}/{processed} sections")
        print(f"All subsections have been saved to: {os.path.abspath(output_dir)}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
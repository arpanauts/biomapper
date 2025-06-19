#!/usr/bin/env python3
"""
Parse Function Health HTML page to extract medical tests and their categories.
"""

import csv
from bs4 import BeautifulSoup
import re


def clean_text(text):
    """Clean and normalize text by removing extra whitespace."""
    if text:
        return ' '.join(text.strip().split())
    return ''


def extract_category_name(category_section):
    """Extract the category name from a category section."""
    # Look for the category title in the family-accent div
    category_div = category_section.find('div', {'data-category': True})
    if category_div:
        return clean_text(category_div.get_text())
    return None


def extract_test_info(test_item):
    """Extract test name and notes from a test item (accordion or regular)."""
    test_name = None
    notes = []
    
    # Try to find test name in biomarker-name div
    name_div = test_item.find('div', attrs={'biomarker-name': True})
    if name_div:
        test_name = clean_text(name_div.get_text())
    
    # Look for indicators (2x, Add on, New)
    indicators = test_item.find_all('div', class_='biomarker-indicator')
    for indicator in indicators:
        # Skip "is-new" indicators as we don't need to track those
        if 'is-new' in indicator.get('class', []):
            continue
        
        # Look for the indicator text
        indicator_text = indicator.find('div', class_=re.compile(r'f-\d+.*weight-500'))
        if indicator_text:
            text = clean_text(indicator_text.get_text())
            if text in ['2x', 'Add on']:
                notes.append(text)
    
    return test_name, ', '.join(notes)


def parse_function_health_html(html_file_path, output_csv_path):
    """Parse the HTML file and extract tests to CSV."""
    
    # Read the HTML file
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the main test listing section
    test_section = soup.find('section', id='alltests')
    if not test_section:
        print("Error: Could not find the 'alltests' section")
        return
    
    # Find all category sections
    # Categories have the pattern with family-accent class
    category_sections = test_section.find_all('div', class_='biomarker-cat')
    
    # Prepare data for CSV
    csv_data = []
    
    for category_section in category_sections:
        # Extract category name
        category_name = extract_category_name(category_section)
        if not category_name:
            continue
        
        # Find all test items in this category
        # Tests are in accordion divs
        test_items = category_section.find_all('div', class_='accordion')
        
        for test_item in test_items:
            test_name, notes = extract_test_info(test_item)
            
            if test_name:
                # If this is in the "Add On" category, ensure "Add on" is in notes
                if category_name == "Add On" and "Add on" not in notes:
                    if notes:
                        notes = f"Add on, {notes}"
                    else:
                        notes = "Add on"
                
                csv_data.append({
                    'Category': category_name,
                    'Test Name': test_name,
                    'Notes': notes
                })
    
    # Write to CSV
    with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Category', 'Test Name', 'Notes']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in csv_data:
            writer.writerow(row)
    
    print(f"Successfully extracted {len(csv_data)} tests to {output_csv_path}")
    
    # Print summary
    categories = {}
    for row in csv_data:
        cat = row['Category']
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1
    
    print("\nSummary by category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} tests")


if __name__ == "__main__":
    html_file = "/home/ubuntu/biomapper/data/function_health/What's Included.html"
    output_csv = "/home/ubuntu/biomapper/data/function_health/function_health_tests.csv"
    
    parse_function_health_html(html_file, output_csv)
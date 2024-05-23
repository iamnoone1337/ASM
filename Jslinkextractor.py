import re
import argparse

def remove_text_patterns_and_lines(file_path, output_file_path=None):
    """
    Remove text of the format "<number> - ./" and "<number> - " and lines containing '+', 'http://', or 'https://'
    from a file, then save the result.
    
    :param file_path: Path to the input text file.
    :param output_file_path: Path to the output text file. If None, overwrite the input file.
    """
    # Read the content of the file
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    modified_lines = []
    for line in lines:
        if '+' in line or 'http://' in line or 'https://' in line:
            continue  # Skip lines containing '+', 'http://', or 'https://'
        # Use regex to find and remove the patterns "<number> - ./" and "<number> - "
        modified_line = re.sub(r'\d+\s*-\s*\./', '', line)
        modified_line = re.sub(r'\d+\s*-\s*', '', modified_line)
        modified_lines.append(modified_line)
    
    # Determine the output file path
    if output_file_path is None:
        output_file_path = file_path
    
    # Write the modified content back to the file
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.writelines(modified_lines)

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Remove text of the format '<number> - ./' and '<number> - ' and lines containing '+', 'http://', or 'https://' from a file.")
    parser.add_argument('file_path', help="Path to the input text file.")
    parser.add_argument('-o', '--output', help="Path to the output text file. If not provided, the input file will be overwritten.")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Call the function with the provided arguments
    remove_text_patterns_and_lines(args.file_path, args.output)

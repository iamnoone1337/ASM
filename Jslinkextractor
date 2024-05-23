import re
import argparse

def remove_text_pattern(file_path, output_file_path=None):
    """
    Remove text of the format "<number> - " from a file and save the result.
    
    :param file_path: Path to the input text file.
    :param output_file_path: Path to the output text file. If None, overwrite the input file.
    """
    # Read the content of the file
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Use regex to find and remove the pattern "<number> - "
    modified_content = re.sub(r'\d+\s*-\s*', '', content)
    
    # Determine the output file path
    if output_file_path is None:
        output_file_path = file_path
    
    # Write the modified content back to the file
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Remove text of the format '<number> - ' from a file.")
    parser.add_argument('file_path', help="Path to the input text file.")
    parser.add_argument('-o', '--output', help="Path to the output text file. If not provided, the input file will be overwritten.")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Call the function with the provided arguments
    remove_text_pattern(args.file_path, args.output)

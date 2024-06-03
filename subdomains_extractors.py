import re
import argparse

def extract_domains(input_file, output_file):
    # Regular expression to match domain names, including multi-level subdomains
    domain_pattern = re.compile(r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b')
    
    # Set to store unique domain names
    unique_domains = set()
    
    # Read the input file
    with open(input_file, 'r') as file:
        for line in file:
            domains = domain_pattern.findall(line)
            for domain in domains:
                unique_domains.add(domain)
    
    # Write the unique domains to the output file
    with open(output_file, 'w') as file:
        for domain in sorted(unique_domains):
            file.write(domain + '\n')

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='Extract unique domain names from a text file.')
    parser.add_argument('input_file', help='The input text file containing domain names.')
    parser.add_argument('output_file', help='The output file to write the unique domain names.')

    args = parser.parse_args()
    
    # Call the function to extract domains with the provided filenames
    extract_domains(args.input_file, args.output_file)

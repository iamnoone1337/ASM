def remove_unwanted_urls(input_file, output_file):
    unwanted_extensions = ['.png', '.svg', '.js', '.woff', '.css']

    # Open input file
    with open(input_file, 'r') as f:
        lines = f.readlines()

    # Remove URLs with unwanted extensions
    filtered_urls = [url.strip() for url in lines if not any(ext in url.strip() for ext in unwanted_extensions)]

    # Write the filtered URLs to the output file
    with open(output_file, 'w') as f:
        f.write('\n'.join(filtered_urls))

# Example usage
if __name__ == "__main__":
    input_file = 'urls.txt'  # Change this to your input file name
    output_file = 'filtered_urls.txt'  # Change this to your output file name
    remove_unwanted_urls(input_file, output_file)

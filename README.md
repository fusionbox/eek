# Eek

Eek is a web crawler that outputs metadata about a website in CSV format.

## Usage

    eek http://example.com/

To save output to a file, use redirection
    
    eek http://example.com/ > ~/some_file.csv

To slow down crawling, use `--delay=[seconds]`

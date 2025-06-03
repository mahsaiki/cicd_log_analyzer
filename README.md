# CI/CD Log Analyzer - README

A simple, easy-to-use web application for analyzing CI/CD pipeline logs from Jenkins, GitHub Actions, and GitLab CI.

## Features

- Upload or paste CI/CD logs for analysis
- Automatic detection of CI/CD platform (Jenkins, GitHub Actions, GitLab CI)
- Identification of failed steps and error context
- AI-powered root cause analysis and fix suggestions using OpenAI
- Clean, responsive web interface

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- OpenAI API key

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/cicd_log_analyzer.git
   cd cicd_log_analyzer
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your OpenAI API key:
   ```
   # On Linux/macOS
   export OPENAI_API_KEY="your-api-key-here"
   
   # On Windows
   set OPENAI_API_KEY=your-api-key-here
   ```

   Alternatively, create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your-api-key-here
   ```

### Running the Application

1. Start the Flask server:
   ```
   python -m src.main
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

1. Paste your CI/CD log content into the text area or upload a log file
2. Click "Analyze Log"
3. View the analysis results, including:
   - Detected CI/CD platform
   - Failed step identification
   - Root cause analysis
   - Suggested fix or next steps

## Customization

### Changing the OpenAI Model

To use a different OpenAI model (e.g., GPT-4 instead of GPT-3.5-turbo), modify the `model` parameter in the `analyze_with_openai` method in `src/routes/analyzer.py`.

### Adding Support for Additional CI/CD Platforms

To add support for other CI/CD platforms, extend the pattern matching in the `detect_platform`, `extract_failed_step`, and `extract_error_context` methods in the `LogParser` class.

## Limitations

- The accuracy of the analysis depends on the quality of the log content and the OpenAI model used
- Very large logs may need to be truncated to fit within token limits
- The application requires an internet connection to access the OpenAI API

## License

This project is licensed under the MIT License - see the LICENSE file for details.
# cicd_log_analyzer

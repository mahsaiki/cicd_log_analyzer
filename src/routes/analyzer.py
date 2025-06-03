import os
from flask import Blueprint, request, jsonify
import re

# Import openai conditionally to handle different versions
try:
    import openai
    # Check if we're using OpenAI v1.0.0+ (new client style)
    OPENAI_NEW_API = hasattr(openai, "OpenAI")
except ImportError:
    OPENAI_NEW_API = False

analyzer_bp = Blueprint('analyzer', __name__)

class LogParser:
    @staticmethod
    def detect_platform(log_content):
        """Detect the CI/CD platform based on log content patterns."""
        # GitHub Actions patterns
        if re.search(r'##\[(group|endgroup|error|warning)\]', log_content) or \
           re.search(r'::(?:error|warning|notice|debug|group|endgroup)::', log_content):
            return "GitHub Actions"
        
        # Jenkins patterns
        elif re.search(r'\[(?:Pipeline|INFO|WARNING|ERROR)\]', log_content) or \
             re.search(r'(?:Started by|Finished: (?:SUCCESS|FAILURE|ABORTED))', log_content):
            return "Jenkins"
        
        # GitLab CI patterns
        elif re.search(r'(?:Running with GitLab Runner|Job succeeded|Job failed)', log_content) or \
             re.search(r'(?:section_start|section_end):\d+:[a-zA-Z0-9_]+', log_content):
            return "GitLab CI"
        
        # Default if no patterns match
        return "Unknown"

    @staticmethod
    def extract_failed_step(log_content, platform):
        """Extract the failed step from the log content based on the platform."""
        failed_step = "Could not identify specific failed step"
        
        if platform == "GitHub Actions":
            # Look for error annotations or failed steps
            error_match = re.search(r'##\[error\](.*?)(?=\n|$)', log_content)
            if error_match:
                failed_step = error_match.group(1).strip()
            else:
                # Look for failed step in GitHub Actions
                step_match = re.search(r'##\[group\](.*?)(?:failed|error)', log_content, re.IGNORECASE)
                if step_match:
                    failed_step = step_match.group(1).strip()
        
        elif platform == "Jenkins":
            # Look for failed stage in Jenkins Pipeline
            stage_match = re.search(r'(?:FAILURE|ERROR).*?Stage "(.*?)"', log_content)
            if stage_match:
                failed_step = f"Stage: {stage_match.group(1)}"
            else:
                # Look for general error messages
                error_match = re.search(r'(?:ERROR|FAILURE): (.*?)(?=\n|$)', log_content)
                if error_match:
                    failed_step = error_match.group(1).strip()
        
        elif platform == "GitLab CI":
            # Look for failed job or script in GitLab CI
            job_match = re.search(r'Running with gitlab-runner.*?\n\$ (.*?)(?=\n|$).*?ERROR: Job failed', 
                                 log_content, re.DOTALL)
            if job_match:
                failed_step = f"Command: {job_match.group(1)}"
            else:
                # Section with error
                section_match = re.search(r'section_start:\d+:(.*?)(?=\n|$).*?(?:error|failed)', 
                                         log_content, re.IGNORECASE | re.DOTALL)
                if section_match:
                    failed_step = f"Section: {section_match.group(1)}"
        
        return failed_step

    @staticmethod
    def extract_error_context(log_content, platform, failed_step):
        """Extract relevant error context from the log content."""
        error_context = "No specific error context found"
        
        # Common error patterns across platforms
        error_patterns = [
            r'(?:error|exception|failure|failed):.*?(?=\n\n|\n[^\s]|$)',
            r'(?:Error|Exception|Failure):.*?(?=\n\n|\n[^\s]|$)',
            r'(?:npm ERR!|pip.*?error:|maven.*?error:).*?(?=\n\n|\n[^\s]|$)',
            r'(?:syntax error|runtime error|compilation failed).*?(?=\n\n|\n[^\s]|$)',
            r'(?:exit code [1-9]\d*).*?(?=\n\n|\n[^\s]|$)'
        ]
        
        for pattern in error_patterns:
            matches = re.finditer(pattern, log_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                error_text = match.group(0).strip()
                if error_text:
                    # Get a few lines before and after for context
                    start_pos = max(0, match.start() - 200)
                    end_pos = min(len(log_content), match.end() + 200)
                    context = log_content[start_pos:end_pos].strip()
                    return context
        
        # Platform-specific fallbacks if common patterns don't match
        if platform == "GitHub Actions":
            error_match = re.search(r'##\[error\].*?(?=\n\n|\n##|\n[^\s]|$)', log_content, re.DOTALL)
            if error_match:
                error_context = error_match.group(0).strip()
        
        elif platform == "Jenkins":
            error_match = re.search(r'ERROR:.*?(?=\n\n|\n[^\s]|$)', log_content, re.DOTALL)
            if error_match:
                error_context = error_match.group(0).strip()
        
        elif platform == "GitLab CI":
            error_match = re.search(r'(?:ERROR|FATAL):.*?(?=\n\n|\n[^\s]|$)', log_content, re.DOTALL)
            if error_match:
                error_context = error_match.group(0).strip()
        
        return error_context

class LLMAnalyzer:
    @staticmethod
    def analyze_with_openai(platform, failed_step, error_context):
        """
        Analyze the log error using OpenAI API.
        
        This method is compatible with both older and newer versions of the OpenAI Python library.
        """
        # Get API key from environment variable
        api_key = os.getenv('OPENAI_API_KEY', 'your_api_key_here')
        
        # Construct the prompt
        prompt = f"""
        You are an expert Senior DevOps Engineer specializing in diagnosing CI/CD pipeline failures. 
        Analyze the provided log snippet from a failed CI/CD job, identify the root cause of the failure, 
        and suggest a specific, actionable fix or the next diagnostic step.

        **CI/CD Platform:** {platform}
        **Failed Step:** {failed_step}

        **Relevant Log Output (Focus on Error):**
        ```
        {error_context}
        ```

        **Analysis Request:**
        1. **Identify Failure:** Briefly state the specific error message or failure condition observed.
        2. **Determine Root Cause:** Based on the log output, explain the most likely reason for the failure.
        3. **Suggest Fix / Next Step:** Provide a concrete code change, configuration adjustment, command modification, or diagnostic command to resolve the issue or gather more information.

        Format your response as a JSON object with the following keys:
        - root_cause: A concise explanation of the root cause
        - suggested_fix: A specific, actionable suggestion to fix the issue
        """
        
        try:
            response_text = ""
                        
                    # Handle different OpenAI library versions
            if OPENAI_NEW_API:
                # New OpenAI client (v1.0.0+) - ADD base_url for OpenRouter
                client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://openrouter.ai/api/v1"  # Add this line
                )
                response = client.chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert CI/CD troubleshooter that responds in JSON format."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                response_text = response.choices[0].message.content
            else:
                # Legacy OpenAI API (pre-v1.0.0) - ADD base_url for OpenRouter
                openai.api_key = api_key
                openai.api_base = "https://openrouter.ai/api/v1"  # Add this line
                response = openai.ChatCompletion.create(
                    model="openai/gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert CI/CD troubleshooter that responds in JSON format."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                response_text = response['choices'][0]['message']['content']
            
            # Extract the root cause and suggested fix using regex
            root_cause_match = re.search(r'"root_cause"\s*:\s*"(.*?)"', response_text, re.DOTALL)
            suggested_fix_match = re.search(r'"suggested_fix"\s*:\s*"(.*?)"', response_text, re.DOTALL)
            
            root_cause = root_cause_match.group(1) if root_cause_match else "Could not determine root cause"
            suggested_fix = suggested_fix_match.group(1) if suggested_fix_match else "No specific fix suggested"
            
            return {
                "root_cause": root_cause,
                "suggested_fix": suggested_fix
            }
            
        except Exception as e:
            # In a production environment, you would want to log this error
            print(f"Error calling OpenAI API: {e}")
            return {
                "root_cause": f"Error analyzing log with AI: {str(e)}",
                "suggested_fix": "Please check your OpenAI API key is set correctly and try again. If the problem persists, you may need to install a compatible version of the OpenAI library (try: pip install openai==0.28.1 for older API or pip install openai>=1.0.0 for newer API)."
            }

@analyzer_bp.route('/analyze', methods=['POST'])
def analyze_log():
    """Analyze the provided CI/CD log."""
    data = request.json
    if not data or 'log' not in data:
        return jsonify({'error': 'No log content provided'}), 400
    
    log_content = data['log']
    
    # Detect the CI/CD platform
    platform = LogParser.detect_platform(log_content)
    
    # Extract the failed step
    failed_step = LogParser.extract_failed_step(log_content, platform)
    
    # Extract error context
    error_context = LogParser.extract_error_context(log_content, platform, failed_step)
    
    # Analyze with OpenAI
    analysis_result = LLMAnalyzer.analyze_with_openai(platform, failed_step, error_context)
    
    # Return the complete analysis
    return jsonify({
        'platform': platform,
        'failed_step': failed_step,
        'error_context': error_context,
        'root_cause': analysis_result['root_cause'],
        'suggested_fix': analysis_result['suggested_fix']
    })

import requests
import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential
from termcolor import colored

load_dotenv()
print(os.getenv("OPENAI_API_KEY"))
GPT_MODEL = "gpt-3.5-turbo-0613"
client = OpenAI()
user_prompt = 'I am hearing a lot about run-llama/llama_index nowadays, if the repository contains more than 10 stars then add a star from myself'

# Chat completion request function with args for tools, which will contain our function definition

@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def chat_completion_request(messages, tools=None, tool_choice=None, model=GPT_MODEL):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e


def get_repo_ratings(repo_name):
    # Split up the repo_name identifier into its consummate parts
    owner, repo = repo_name.split('/')

    # Make API request to get the number of stars
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        stars_count = data['stargazers_count']
        print(f"The repository {owner}/{repo} has {stars_count} stars.")

        # Check if stars count exceeds threshold and decide whether to star the repository
        threshold = 10
        if stars_count > threshold:
            print(f"Since the repository has more than {threshold} stars, I would add a star.")
        else:
            print(f"The repository doesn't meet the threshold of {threshold} stars, so no star would be added.")
    else:
        print(f"Failed to fetch data from GitHub API. Status code: {response.status_code}")

# Method: execute_function_call(message)
# Execute function name defined inside of message with repo_name separately gleaned from
#   accompanying arguments
def execute_function_call(message):
    if message.tool_calls[0].function.name == "get_repo_ratings":
        repo_name = json.loads(message.tool_calls[0].function.arguments)["repo_name"]
        results = get_repo_ratings(repo_name)
    else:
        results = f"Error: function {message.tool_calls[0].function.name} does not exist"
    return results

# Definition of the conceptual function we'll use to define the
# underlying Python function to retrieve the star ratings for GitHub projects
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_repo_ratings",
            "description": "Get the number of stars for a github repo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Name of the repo",
                    },
                },
                "required": ["repo_name"],
            },
        }
    }
]

messages = []
messages.append({"role": "system",
                 "content": "If the repository contains more than 10 stars then I should add a start to the repo.  Tell me if I should add a star."})
messages.append({"role": "user", "content": user_prompt})
chat_response = chat_completion_request(messages, tools)
assistant_message = chat_response.choices[0].message
assistant_message.content = str(assistant_message.tool_calls[0].function)
messages.append({"role": assistant_message.role, "content": assistant_message.content})
if assistant_message.tool_calls:
    results = execute_function_call(assistant_message)
    messages.append({"role": "function", "tool_call_id": assistant_message.tool_calls[0].id,
                     "name": assistant_message.tool_calls[0].function.name, "content": results})
print(messages)

print("Secondary Testing")

name_to_test = "dexstakker/scrabbler"
get_repo_ratings(name_to_test)
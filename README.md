<<<<<<< HEAD
🤖 Agentic Patterns Showcase
A Python project demonstrating foundational agentic patterns using the OpenAI SDK and models accessed via the OpenRouter service. This repository is structured for exploring and developing different model-based architectures, starting with a simple chat agent.

Table of Contents
Project Overview

Project Structure

Features

Installation and Setup

Usage

Technologies Used

License

Contact

Project Overview
Streamlit front end to a python OpenAI back end that uses LLM to create resume based on job advertisement and other user information.


Evaluator Architecture: Demonstrates how to use a superior "evaluator" model to feedback to writer models to iterate on the resume until it is acceptable.

OpenRouter Integration: Configured to use OpenRouter API endpoints for broader model access and cost management.

Modular Design: Separates core agent logic, evaluation logic, and shared configurations for easier development of new patterns.

Installation and Setup
This project requires Python and access to language models via the OpenRouter API.

Prerequisites
Python 3.9+

An OpenRouter API Key.

Setup Steps
Clone the repository:

git clone https://github.com/johnsonadam187gmail/basic_chat_agent.git

Install dependencies:
The project relies on the openai package and likely python-dotenv for environment management.


# Install the necessary packages
uv sync

Configure Environment Variables:
Create a file named .env in the root directory (my-awesome-project/) and add your API key:

# .env file content
OPENROUTER_API_KEY="YOUR_OPENROUTER_KEY_HERE"

Note: The packages/environment.py file should handle loading this key and setting the appropriate base URL for the OpenAI client.

Technologies Used
Primary Language: Python

SDK: OpenAI SDK (used for making model calls)

API Service: OpenRouter (for flexible model access)

Dependency Management: uv

=======
# cv_app_deploy
AI agent CV app deploy with Streamlit
>>>>>>> 8c02e3f2d5f19e2bfda2a211a78d251cf2c976e2

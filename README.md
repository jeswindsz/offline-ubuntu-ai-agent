# Offline Ubuntu AI Agent

An intelligent, privacy-focused desktop assistant built to interact with and control an Ubuntu Linux system using natural language commands. Powered by locally hosted Large Language Models (LLMs) through Ollama, the agent enables users to perform everyday desktop operations without depending on cloud-based AI services.

The project features two AI modes — a lightweight model for quick, routine tasks and a larger model for complex instructions and deep reasoning — providing a balance between speed and intelligence.

## Features

- **Offline AI Processing:** Runs AI models locally using Ollama, keeping interactions on the user's machine.
- **Natural Language Interaction:** Execute supported desktop operations using everyday language.
- **Dual AI Model Modes:** Switch between lightweight processing and deeper reasoning.
- **Application Management:** Launch and interact with supported desktop applications.
- **File Management:** Perform supported file operations through natural language instructions.
- **System Interaction:** Navigate and interact with selected Ubuntu desktop features.
- **Safety and Confirmation:** Sensitive actions require user confirmation before execution.

## AI Model Modes

The agent supports two model modes designed for different levels of task complexity.

### `/modelsmall` — Quick Processing

Uses the smaller, lightweight AI model for simple and routine tasks.

Suitable for:
- Opening applications
- Basic file operations
- Simple desktop commands
- Quick system navigation
- Everyday assistant tasks

This mode prioritizes faster responses and lower resource usage.

### `/modelbig` — Deep Thinking

Uses the larger AI model for complex instructions and tasks requiring more detailed reasoning.

Suitable for:
- Multi-step desktop instructions
- Complex task interpretation
- More detailed planning
- Advanced command understanding
- Tasks requiring deeper reasoning

This mode prioritizes reasoning capability over response speed and may require more system resources.

## Technologies Used

- Python
- Ollama
- Qwen3
- Ubuntu Linux
- GNOME Desktop Environment
- D-Bus

## Project Objective

The objective of this project is to develop a locally running AI desktop assistant capable of understanding natural language and performing useful computer operations securely.

By combining offline AI processing with multiple model modes, the project aims to provide a practical Linux assistant that balances privacy, performance, and intelligent desktop automation.

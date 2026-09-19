# AI-Powered Restaurant Recommendation System (Zomato Use Case)

## Overview

You are tasked with building an AI-powered restaurant recommendation service inspired by Zomato. The system should intelligently suggest restaurants based on user preferences by combining structured data with a Large Language Model (LLM).

## Objective

Design and implement an application that:

- Takes user preferences (such as location, budget, cuisine, and ratings)
- Uses a real-world dataset of restaurants
- Leverages an LLM to generate personalized, human-like recommendations
- Displays clear and useful results to the user

## System Workflow

### 1. Data Ingestion

- Load and preprocess the Zomato dataset from Hugging Face: [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
- Extract relevant fields such as restaurant name, location, cuisine, cost, rating, etc.

### 2. User Input

Collect user preferences:

- **Location** (e.g., Delhi, Bangalore)
- **Budget** (low, medium, high)
- **Cuisine** (e.g., Italian, Chinese)
- **Minimum rating**
- **Any additional preferences** (e.g., family-friendly, quick service)

### 3. Integration Layer

- Filter and prepare relevant restaurant data based on user input
- Pass structured results into an LLM prompt
- Design a prompt that helps the LLM reason and rank options

### 4. Recommendation Engine

Use the LLM to:

- Rank restaurants
- Provide explanations (why each recommendation fits)
- Optionally summarize choices

### 5. Output Display

Present top recommendations in a user-friendly format:

- Restaurant Name
- Cuisine
- Rating
- Estimated Cost
- AI-generated explanation

## Key Components Summary

| Component | Responsibility |
|-----------|----------------|
| Dataset | Zomato restaurant data from Hugging Face |
| User Input | Location, budget, cuisine, rating, and custom preferences |
| Filtering Layer | Narrow dataset based on user criteria |
| LLM | Rank, explain, and summarize recommendations |
| Output | Structured, human-readable restaurant suggestions |

## Data Source

- **Dataset URL:** https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation
- **Key fields:** restaurant name, location, cuisine, cost, rating

## Expected User Experience

1. User provides their dining preferences.
2. System filters the restaurant dataset to match those preferences.
3. LLM analyzes the filtered results and produces ranked recommendations with explanations.
4. User sees a clear list of top restaurant picks with relevant details and AI-generated reasoning.

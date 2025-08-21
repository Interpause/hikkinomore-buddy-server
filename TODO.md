# TODO

## Exact

- Improve skill descriptions. Should include:
  - Explanation of social skill
  - Criteria for demonstrating (or not) the social skill (from 1.0 to -1.0 performance)
  - Optional examples
- Skills should be dynamically loaded from a directory (similar to agents.prompts)
  - Have some way to pass skill agent the list of active/disabled skills
- Display some info to the user? Then they enter their feedback into a Google form link?
- Use "start" as a fixed example to let us choose if model or user starts first
  - For prompted scenario, special keyword triggers initial message from bot, then also tells the server to load a specific prompt set
- Per user per convo loggers of the convo, skill judgements, etc for eval

## High-Level

- A/B Prompts for chatbots
- Better skill prompts for evaluation
- Chatbot steered by skill history and user profile
- Prompted scenarios

Naturally this means the buddy should prompt the convo itself if idle for a while
instead of waiting for user, similar as the SillyTavern thing

## Postponed

- User profile consisting of past convos, profiling, user imput, and social skill history.
- Detect opportunity during natural convo for skill development and have AI inject qns/direct convo towards scenario
- Detect skill attained passively in natural convo

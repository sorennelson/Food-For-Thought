# Food For Thought

> A FastAPI webhook that delivers daily Food For Thought entries to IFTTT applets (e.g. Day One) using a Langchain LLM to extract ideas from the most recent The Tim Ferriss Show episode.

This repo was built with the following: FastAPI, Langchain, Gemini-2.5-flash, Redis, Docker, cron. The webhook is hosted on an AWS EC2 instance.

Ideas for Food For Thought entries are generated based on [transcripts from The Tim Ferriss Show.](https://tim.blog/2018/09/20/all-transcripts-from-the-tim-ferriss-show/)

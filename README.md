# Food For Thought

> A FastAPI webhook that delivers daily Food For Thought entries to IFTTT applets (e.g. Day One) using a Langchain LLM to extract ideas from the most recent The Tim Ferriss Show episode.

The app uses a weekly cron job to create 7 days of FFT entries from the latest transcript and a daily cron job to create the current day. Built with the following technologies: FastAPI, Langchain, Gemini-2.5-flash, Redis, Docker, cron. All hosted on an AWS EC2 instance.

Transcripts are extracted from [The Tim Ferriss Show Transcripts](https://tim.blog/2018/09/20/all-transcripts-from-the-tim-ferriss-show/).

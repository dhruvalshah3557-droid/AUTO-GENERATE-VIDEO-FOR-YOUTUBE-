# MoneyPrinterTurbo

An all-in-one AI short video generator. Provide a topic, article URL, or hot-list item and the app writes a script, matches footage, synthesizes voiceover, burns subtitles, and exports an HD short.

## Features

- Auto Studio: finds trending topics, writes scripts, and renders videos; you only preview and keep or skip
- Four-column Manual Studio matching MoneyPrinterTurbo
- Built-in writer plus optional OpenAI-compatible LLM
- Free Edge TTS (no key) with 小简 / 老陈 dual-voice for dialogue styles
- Pexels, Wikimedia, and generated color clips as footage fallback
- URL-to-video: fetch a public article and turn it into a short
- Script styles: narration, podcast, crosstalk, talkshow
- Hot list picker for trending topics

Inspired by [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) and [AI-Short-Video-Engine](https://github.com/chenwr727/AI-Short-Video-Engine).

## Run

```
npm install
npm run dev
```

WebUI: http://127.0.0.1:8501

API: http://127.0.0.1:8080/docs

Edge TTS is free and needs no key. Pexels and an OpenAI-compatible LLM are optional.

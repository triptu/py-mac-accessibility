# macOS Accessibility Browser

A Streamlit web app for exploring macOS application accessibility trees with visual screenshots and interactive JSON data. Features -

- shows all running applications(fetched using AppleScript)
- screenshot with highlighted UI elements
- accessibility tree as an interactive JSON
- summary statisitics for the accessibility tree


### Install Deps

```sh
uv sync
```

### Run the app

It will also open the page in your default browser.

```sh
uv run streamlit run app.py
```

### Debugging

- Ensure you've given accessibility permission to the terminal you're using to run this app(Settings -> Privacy -> Accessibility). Optionally also give screen recording permission(Settings -> Privacy -> Screen Recording) to see screenshots.
- Note that the app's window should be visible on the screen. You might need to exit full screen mode for the webapp, to have two windows visible at the same time, if you're not using a separate monitor.

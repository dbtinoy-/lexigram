Output hero/lexigram-hero.gif

# Settings
Set FontSize 14
Set Width 1280
Set Height 720
Set Theme "catppuccin-mocha"
Set Padding 16
Set Framerate 3
Set PlaybackSpeed 2.0
Set TypingSpeed 10ms

# Set up pg alias (stays visible)
Type "alias pg='pygmentize -g -O style=monokai,linenos=1,linenostart=0 2>/dev/null'" Sleep 0ms
Enter
Sleep 100ms
Type "cd ~/lexigram-demos/hero" Sleep 0ms
Enter
Sleep 100ms

# Panel 1: ##1 → ##2 (23 lines, fits in window)
Ctrl+L
Sleep 100ms
Type "sed -n '/^##1/,/^##2/p' app.py|sed '/^##/d'|pg|head -35" Sleep 0ms
Enter
Sleep 4s

# Panel 2: ##2 → ##3 (37 lines, truncated to top 35)
Ctrl+L
Sleep 100ms
Type "sed -n '/^##2/,/^##3/p' app.py|sed '/^##/d'|pg|head -35" Sleep 0ms
Enter
Sleep 4s

# Panel 3: ##3 → ##4 (50 lines, truncated to top 35)
Ctrl+L
Sleep 100ms
Type "sed -n '/^##3/,/^##4/p' app.py|sed '/^##/d'|pg|head -35" Sleep 0ms
Enter
Sleep 4s

# Panel 4: ##4 → ##5 (47 lines, truncated to top 35)
Ctrl+L
Sleep 100ms
Type "sed -n '/^##4/,/^##5/p' app.py|sed '/^##/d'|pg|head -35" Sleep 0ms
Enter
Sleep 4s

# Panel 5: ##5 → ##6 (64 lines, truncated to top 35)
Ctrl+L
Sleep 100ms
Type "sed -n '/^##5/,/^##6/p' app.py|sed '/^##/d'|pg|head -35" Sleep 0ms
Enter
Sleep 4s

# Panel 6: ##6 → end (88 lines, truncated to top 35)
Ctrl+L
Sleep 100ms
Type "awk '/^##6/{f=1;next} f' app.py | pg | head -35" Sleep 0ms
Enter
Sleep 4s

# Run the real demo (live local LLM calls: Ollama + LM Studio, ~60s + 3s pauses)
Ctrl+L
Sleep 100ms
Type "time uv run python3 app.py" Sleep 0ms
Enter
Sleep 100s

# Final delay before GIF loop restart (demo output stays visible)
Sleep 15s

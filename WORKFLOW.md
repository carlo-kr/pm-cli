# Daily Workflow Guide

A practical guide for using PM CLI in your daily work routine.

## 🎯 The Core Workflow Loop

**Morning Planning → Daily Execution → Evening Reflection → Repeat**

This workflow is designed around three core principles:
1. **Plan when fresh** - Morning planning with a clear mind
2. **Track as you go** - Continuous progress updates throughout the day
3. **Small daily batches** - Focus on 3-5 realistic todos, not 20

---

## 🌅 Morning Planning Session (15-20 min)

Start your day by reviewing progress and setting clear priorities.

### 1. Open Your Daily Standup

```bash
pm standup
```

This shows you:
- Top 5 projects by priority and health
- Your in-progress todos
- Recent commits from yesterday
- Top priorities across all projects

**Example output:**
```
📋 Daily Standup
Monday, February 10, 2026

Top 5 Projects:
1. EarnScreen (Health: 75/100 - Good)
   🔵 #15 - Implement authentication (Priority: 85.8, in_progress)
   ⚪ #16 - Design reward badges (Priority: 71.2)
   Recent: 3 commits yesterday

What would you like to do?
❯ Start next todo
  View metrics
  View activity
  Exit
```

### 2. Plan Your Day (Interactive)

```bash
pm plan-day
```

This interactive workflow:
- Shows yesterday's accomplishments
- Displays top 10 priorities
- Lets you select 3-5 todos for today
- Tags them with "today" for easy filtering
- Shows your daily plan

**Tips for picking todos:**
- **Mix effort levels**: 1 hard (L/XL), 2 medium (M), 1-2 quick wins (S)
- **Consider energy**: Schedule hard tasks for your peak hours
- **Be realistic**: 3-5 is better than 10 half-done tasks
- **Check deadlines**: Prioritize anything due soon

### 3. Review Project Metrics (Optional)

```bash
# Quick health check on your main projects
pm metrics EarnScreen
pm metrics pm

# Detailed view with trends
pm metrics EarnScreen --detailed
```

Look for:
- Health scores trending down (needs attention)
- Velocity changes (are you slowing down?)
- Overdue todos (need to address or reschedule)

### 4. Sync Yesterday's Work

```bash
# Pull in commits from yesterday
pm sync --all
```

This links your git commits to todos and updates project activity.

### 5. Start Your First Task

```bash
pm start
```

This picks your highest priority todo and marks it as "in_progress".

---

## ☀️ During the Day (Continuous)

Stay focused and track progress as you work.

### Starting a Task

```bash
# Interactive: picks next priority
pm start

# Or manually start a specific todo
pm todo start 15
```

**You'll see:**
```
🚀 Ready to work on:
  Project: EarnScreen
  Todo: #15 - Implement user authentication

💡 Tips:
  • Reference this todo in commits: git commit -m "fix: ... (#15)"
  • When done: pm todo complete 15
```

### Working on the Task

Focus on the task at hand. Reference it in your commits:

```bash
git commit -m "feat: add login form (#15)"
git commit -m "test: add authentication tests (#15)"
git commit -m "feat: complete user authentication (fixes #15)"
```

**Commit message patterns that PM understands:**
- `#15` or `#T15` - Links commit to todo #15
- `fixes #15`, `closes #15`, `resolves #15`, `completes #15` - Links and auto-completes todo

### Completing a Task

```bash
# Option 1: Manual completion
pm todo complete 15

# Option 2: Auto-complete via commit (if you used "fixes #15")
pm sync EarnScreen  # Syncs commit and auto-completes todo
```

You'll see:
```
🎉 Todo #15 marked as completed!
   Priority recalculated for EarnScreen project
```

### What's Next?

```bash
# See your today's todos
pm todos --today

# Or all top priorities
pm todos --next

# Then pick the next one
pm start
```

### When You Get Blocked

Don't let blockers slow you down silently - track them!

```bash
# Mark as blocked
pm todo block 15 --by 16

# Or create the blocker todo first
pm todo add EarnScreen "Get API key from ops team" --effort S --today
pm todo block 15 --by 17
```

Blocked todos drop in priority (0.5x reduction), so PM will suggest other work.

### Mid-Day Check-In (Optional)

```bash
# Quick status
pm todos --today

# See what's done vs remaining
```

Adjust your plan if needed - it's okay to move things to tomorrow if priorities shifted.

---

## 🌙 Evening Reflection (5-10 min)

Close the loop on your day with a quick review.

### 1. Sync Your Work

```bash
pm sync --all
```

This captures all today's commits and links them to todos.

### 2. Review Accomplishments

```bash
pm review
```

**Output shows:**
```
📊 Daily Review

Top 5 Projects:

EarnScreen
  Health: 78/100 - Good (+3 from yesterday)
  Completed: 2 todos today
  Commits: 5 (last: 30 minutes ago)
  Top priorities:
    • #16 - Design reward badges (71.2)
    • #18 - Add analytics tracking (68.5)

pm
  Health: 67.5/100 - Good
  Completed: 1 todo today
  ...
```

### 3. Check Metrics (Optional)

```bash
pm metrics EarnScreen --detailed
```

Look at:
- **Velocity**: Did you complete what you planned?
- **Completion rate**: Trending up or down?
- **Health score**: Project health improving?

### 4. Update Any Blockers

```bash
# If something is blocked
pm todo block 18 --by 19

# Update priorities if needed
pm prioritize EarnScreen
```

### 5. Quick Tomorrow Preview

```bash
# Glance at what's coming
pm todos --next
```

**Don't plan in detail yet** - just get a sense of tomorrow. You'll do real planning in the morning when your mind is fresh.

---

## 📅 Example: A Full Day

### 🌅 Morning (8:00 AM)

```bash
pm plan-day
```

**You select 4 todos for today:**
1. #15 - Implement user authentication (M effort)
2. #16 - Design reward badges (L effort)
3. #20 - Fix login redirect bug (S effort)
4. #22 - Update README (S effort)

```bash
# Start the day
pm start

# Output:
🚀 Ready to work on:
  Project: EarnScreen
  Todo: #15 - Implement user authentication
```

### ☀️ Mid-Morning (10:30 AM)

```bash
# You finish authentication
git commit -m "feat: implement user authentication (fixes #15)"

# Complete the todo
pm todo complete 15

# What's next from today's plan?
pm todos --today
```

**Output shows 3 remaining:**
- #16 - Design reward badges
- #20 - Fix login redirect bug
- #22 - Update README

```bash
# Pick next one
pm start  # Automatically picks #16
```

### 🌆 Afternoon (2:00 PM)

You realize #16 is taking longer than expected.

```bash
# Check status
pm todos --today

# Decide to defer #22 to tomorrow
# No action needed - just don't work on it

# Focus on #20 (quick win) instead
pm todo start 20
```

### 🌙 Evening (5:30 PM)

```bash
# Sync your work
pm sync --all

# See what you accomplished
pm review
```

**Output:**
```
Completed Today:
  • #15 - Implement user authentication ✓
  • #20 - Fix login redirect bug ✓
  • #16 - Design reward badges ✓ (just finished!)

Still Open:
  • #22 - Update README (deferred to tomorrow)

Commits: 7 across 2 projects
Velocity: 0.43 todos/day (up from 0.29!)

🎉 Great day! You completed 3 todos.
```

```bash
# Quick preview tomorrow
pm todos --next

# See #22 at the top (tagged "today" but not done)
```

---

## 🎯 Quick Reference Commands

### Morning
```bash
pm standup              # Daily overview
pm plan-day             # Interactive planning
pm todos --today        # See today's plan
pm start                # Begin first task
```

### During Day
```bash
pm start                # Pick next task
pm todo complete 15     # Mark as done
pm todos --today        # Check today's status
pm todos --next         # See all priorities
pm todo block 18 --by 19  # Mark as blocked
```

### Evening
```bash
pm sync --all           # Sync today's commits
pm review               # See accomplishments
pm metrics <project>    # Check health
pm todos --next         # Preview tomorrow
```

---

## 💡 Pro Tips

### 1. Use Git Commit Integration

Always reference todos in commits:
```bash
git commit -m "feat: add login form (#15)"
```

This automatically:
- Links the commit to todo #15
- Shows up in `pm todo show 15`
- Updates project activity
- Can auto-complete todos with "fixes #15"

### 2. Tag Strategically

Use tags to organize work:
```bash
pm todo add "Fix bug" --tags "urgent,bug,frontend"
```

Then filter:
```bash
pm todos --tag urgent
```

### 3. Effort Sizing Matters

Be honest about effort:
- **S** (< 2 hours) - Quick wins, boosts morale
- **M** (2-4 hours) - Solid work chunks
- **L** (4-8 hours) - Major tasks, plan full day
- **XL** (> 8 hours) - Break into smaller todos

Small efforts score higher in priority (quick wins!).

### 4. Review Weekly, Not Just Daily

```bash
# Friday afternoon
pm metrics --all
pm report EarnScreen --format markdown
```

Look for patterns:
- Which projects are stalling?
- What's blocking progress?
- Where should you focus next week?

### 5. Use Interactive Commands

Don't remember all the commands? Use interactive workflows:
```bash
pm start      # Pick todo interactively
pm standup    # Interactive daily standup
pm plan-day   # Interactive planning
```

### 6. Sync Often

```bash
# After a good chunk of work
pm sync --all
```

Frequent syncing means:
- Accurate activity tracking
- Auto-completed todos
- Better priority calculations

### 7. Be Realistic

**Better to complete 3 todos than to half-finish 10.**

If you consistently don't finish your daily plan:
- You're planning too much
- Reduce to 2-3 todos per day
- Adjust estimates after a week of data

---

## 🚀 Advanced Workflows

### Weekly Planning

```bash
# Monday morning
pm goals EarnScreen                    # Review goals
pm goal add EarnScreen "Launch v1.0" \
  --priority 95 \
  --target 2026-03-01

# Break down into todos
pm todo add EarnScreen "Complete authentication" --goal 5 --effort L
pm todo add EarnScreen "Design onboarding flow" --goal 5 --effort M
pm todo add EarnScreen "Write deployment docs" --goal 5 --effort M
```

### Sprint Planning

```bash
# Start of sprint
pm todos --project EarnScreen          # See all project todos
pm prioritize EarnScreen               # Recalculate priorities

# Tag sprint todos
pm todo update 15 --tags "sprint-3,must-have"
pm todo update 16 --tags "sprint-3,nice-to-have"

# View sprint todos
pm todos --tag sprint-3
```

### Project Handoff

```bash
# Export all project data
pm export EarnScreen --output earnscreen-handoff.json

# Generate report
pm report EarnScreen --format markdown --output STATUS.md

# Share with team
```

---

## 📊 Workflow Principles

### Why Morning Planning?

**✅ Pros:**
- Fresh mind, better decisions
- Realistic about the day ahead
- Can adapt to overnight changes
- More strategic thinking

**❌ Cons of evening planning:**
- Mental fatigue after full day
- Over-planning when tired
- Plans become stale by morning

### Why 3-5 Todos?

**Research shows:**
- Most people can do 2-4 hours of deep work per day
- Meetings/interruptions take 2-3 hours
- Context switching kills productivity

**3-5 todos = realistic + achievable + motivating**

### Why Track as You Go?

**Benefits:**
- Accurate data for future planning
- Visible progress (motivating!)
- Better priority calculations
- Proof of impact (for reviews, metrics)

**Without tracking:**
- No data to improve
- Unclear what actually happened
- Poor estimates forever

---

## 🎯 Success Metrics

Track these to know if your workflow is working:

### Daily
- **Completion rate**: Did you finish your daily plan? (Target: 70-80%)
- **Focus**: Did you work on priorities? (Check: were your commits on planned todos?)

### Weekly
- **Velocity**: Todos completed per day (Track trend, not absolute number)
- **Health scores**: Projects improving or declining?

### Monthly
- **Goal progress**: Are goals advancing? (Check: todos completed per goal)
- **Project health**: Overall health scores trending up?

---

## 🤝 Working with Others

### Daily Standups (Team)

```bash
pm standup  # Run this before team standup
```

Use the output to share:
- What you completed yesterday
- What you're working on today
- Any blockers

### Progress Updates

```bash
# Generate status report
pm report EarnScreen --format markdown

# Share metrics
pm metrics EarnScreen
```

### Commit Messages

Good commit messages help your team AND your PM tracking:

```bash
# ✅ Good
git commit -m "feat: add user authentication (#15)

Implements JWT-based auth with refresh tokens.
Closes #15"

# ❌ Bad
git commit -m "stuff"
```

---

## 📚 Next Steps

- Read [TUTORIAL.md](TUTORIAL.md) for detailed command reference
- Check [README.md](README.md) for installation and features
- See [CONTRIBUTING.md](.github/CONTRIBUTING.md) to extend the tool

**Happy planning!** 🚀

"""
╔═══════════════════════════════════════════════════════════════╗
║       UNIVERSAL AUTONOMOUS OS AGENT v4.0                      ║
║  Can do ANY task: GUI, Web, Files, Code, System, Research     ║
║  Architecture: ReAct + Reflexion + Self-Modification          ║
║  Execution: 100% Local · Zero API · Zero Rate Limit           ║
╠═══════════════════════════════════════════════════════════════╣
║  WHAT'S NEW IN v4.0:                                          ║
║  • Universal task decomposition (breaks ANY goal into steps)  ║
║  • Multi-modal perception (UI tree + OCR + pixel + a11y)      ║
║  • Robust error recovery with exponential backoff             ║
║  • Dynamic tool creation (builds new tools on the fly)        ║
║  • Parallel action support                                    ║
║  • Web scraping & API interaction                             ║
║  • Natural language file/folder operations                    ║
║  • Process & service management                               ║
║  • Registry & system configuration                            ║
║  • Multi-window orchestration                                 ║
║  • Smart waiting (event-based, not just sleep)                ║
║  • Context-aware error correction                             ║
║  • Persistent learning across sessions                        ║
║  • Self-modification with safe rollback                       ║
╚═══════════════════════════════════════════════════════════════╝

USAGE:
  python agent.py "any task described in plain English"
  python agent.py --improve "task"           # Learn from execution
  python agent.py --self-improve             # Dedicated improvement session
  python agent.py --review-memory            # Show learned strategies
  python agent.py --rollback                 # Revert last self-patch
  python agent.py --safe "task"              # Confirm destructive ops
  python agent.py --max-steps 50 "task"      # More steps for complex tasks
  python agent.py --verbose "task"           # Extra debug output
  python agent.py --plan-only "task"         # Show plan without executing
  python agent.py --resume                   # Resume last interrupted task
"""

import os
import re
import sys
import ast
import json
import time
import copy
import math
import shutil
import socket
import struct
import hashlib
import argparse
import textwrap
import requests
import subprocess
import webbrowser
import traceback
import difflib
import fnmatch
import glob
import signal
import threading
import tempfile
import platform
import ctypes
import winreg
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any, Dict, List, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

# ─────────────────────────────────────────────────────
# OPTIONAL IMPORTS — graceful degradation
# ─────────────────────────────────────────────────────
CAPABILITIES = {}

try:
    from PIL import Image, ImageGrab, ImageDraw, ImageFont
    CAPABILITIES["pil"] = True
except ImportError:
    CAPABILITIES["pil"] = False

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
    CAPABILITIES["pyautogui"] = True
except ImportError:
    CAPABILITIES["pyautogui"] = False

try:
    import pytesseract
    # Try common install locations
    for tesseract_path in [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]:
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            break
    CAPABILITIES["ocr"] = True
except ImportError:
    CAPABILITIES["ocr"] = False

try:
    import uiautomation as auto
    CAPABILITIES["uiautomation"] = True
except ImportError:
    CAPABILITIES["uiautomation"] = False

try:
    import pyperclip
    CAPABILITIES["clipboard"] = True
except ImportError:
    CAPABILITIES["clipboard"] = False

try:
    import psutil
    CAPABILITIES["psutil"] = True
except ImportError:
    CAPABILITIES["psutil"] = False

try:
    from bs4 import BeautifulSoup
    CAPABILITIES["beautifulsoup"] = True
except ImportError:
    CAPABILITIES["beautifulsoup"] = False

try:
    import win32gui
    import win32con
    import win32api
    import win32process
    CAPABILITIES["win32"] = True
except ImportError:
    CAPABILITIES["win32"] = False

try:
    import keyboard as kb_module
    CAPABILITIES["keyboard"] = True
except ImportError:
    CAPABILITIES["keyboard"] = False

try:
    import mouse as mouse_module
    CAPABILITIES["mouse"] = True
except ImportError:
    CAPABILITIES["mouse"] = False


# ─────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-v3.1:671b-cloud"
AGENT_LOG = "agent_log.jsonl"
WORKSPACE = "agent_workspace"
MEMORY_FILE = "agent_memory.json"
REFLECTION_LOG = "agent_reflections.jsonl"
PATCH_HISTORY = "agent_patches/"
BACKUP_DIR = "agent_backups/"
AGENT_SOURCE = __file__
IMPROVEMENT_LOG = "agent_improvements.jsonl"
STRATEGY_DB = "agent_strategies.json"
TASK_STATE_FILE = "agent_task_state.json"
DYNAMIC_TOOLS_DIR = "agent_dynamic_tools/"
SCREENSHOTS_DIR = "agent_screenshots/"

# Ensure directories exist
for d in [PATCH_HISTORY, BACKUP_DIR, DYNAMIC_TOOLS_DIR,
          SCREENSHOTS_DIR, WORKSPACE]:
    Path(d).mkdir(exist_ok=True)

# Platform detection
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"
SCREEN_WIDTH, SCREEN_HEIGHT = (
    pyautogui.size() if CAPABILITIES.get("pyautogui") else (1920, 1080)
)


# ─────────────────────────────────────────────────────
# LOGGING & DISPLAY
# ─────────────────────────────────────────────────────
class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_BLUE = "\033[44m"

    @staticmethod
    def supports_color():
        try:
            if IS_WINDOWS:
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(
                    kernel32.GetStdHandle(-11), 7
                )
            return True
        except Exception:
            return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


USE_COLOR = Colors.supports_color()


def c(text: str, color: str) -> str:
    """Colorize text if terminal supports it."""
    if USE_COLOR:
        return f"{color}{text}{Colors.RESET}"
    return text


def log_event(event: dict, logfile: str = AGENT_LOG):
    event["ts"] = datetime.now().isoformat()
    event["platform"] = platform.system()
    try:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")
    except Exception:
        pass


def banner(text: str, char="─", width=62, color=Colors.CYAN):
    print(c(f"\n{char * width}", color))
    for line in textwrap.wrap(text, width - 4):
        print(c(f"  {line}", color))
    print(c(f"{char * width}", color))


def step_header(step: int, max_steps: int, phase: str = ""):
    phase_str = f" [{phase}]" if phase else ""
    print(c(
        f"\n{'─' * 20} STEP {step}/{max_steps}{phase_str} {'─' * 20}",
        Colors.BLUE
    ))


def print_action(action_name: str, detail: str = ""):
    icon = "▶"
    print(c(f"  {icon} {action_name}", Colors.YELLOW) +
          (f" {detail}" if detail else ""))


def print_result(success: bool, message: str):
    if success:
        print(c(f"  ✓ {message[:200]}", Colors.GREEN))
    else:
        print(c(f"  ✗ {message[:200]}", Colors.RED))


def print_thought(thought: str):
    print(c(f"  💭 {thought}", Colors.MAGENTA))


# ─────────────────────────────────────────────────────
# MEMORY SYSTEM — Persistent Learning
# ─────────────────────────────────────────────────────
class AgentMemory:
    """
    Persistent memory that survives across sessions.
    Stores strategies, failures, tool reliability,
    task decomposition patterns, and timing data.
    """

    def __init__(self, filepath: str = MEMORY_FILE):
        self.filepath = filepath
        self.data = self._load()

    def _load(self) -> dict:
        if Path(self.filepath).exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        return {
            "learned_strategies": [],
            "failure_patterns": [],
            "tool_notes": {},
            "code_improvements": [],
            "task_decompositions": {},
            "environment_facts": {},
            "custom_tools": [],
            "performance_stats": {
                "total_tasks": 0,
                "successful_tasks": 0,
                "total_steps": 0,
                "avg_steps": 0,
                "fastest_task": None,
                "common_errors": {},
                "tool_usage_counts": {},
                "task_type_success": {}
            },
            "version": 4,
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }

    def save(self):
        self.data["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(c(f"  [Memory] Save failed: {e}", Colors.RED))

    def add_strategy(self, task_pattern: str, strategy: dict):
        self.data["learned_strategies"].append({
            "pattern": task_pattern,
            "strategy": strategy,
            "timestamp": datetime.now().isoformat(),
            "success": True
        })
        self.data["learned_strategies"] = \
            self.data["learned_strategies"][-200:]
        self.save()

    def add_failure(self, context: str, error: str, lesson: str):
        self.data["failure_patterns"].append({
            "context": context,
            "error": error,
            "lesson": lesson,
            "timestamp": datetime.now().isoformat()
        })
        self.data["failure_patterns"] = \
            self.data["failure_patterns"][-100:]
        stats = self.data["performance_stats"]
        error_key = error[:100]
        stats["common_errors"][error_key] = \
            stats["common_errors"].get(error_key, 0) + 1
        self.save()

    def add_tool_note(self, tool: str, note: str):
        if tool not in self.data["tool_notes"]:
            self.data["tool_notes"][tool] = []
        self.data["tool_notes"][tool].append({
            "note": note,
            "timestamp": datetime.now().isoformat()
        })
        self.data["tool_notes"][tool] = \
            self.data["tool_notes"][tool][-20:]
        self.save()

    def add_environment_fact(self, key: str, value: str):
        """Store discovered facts about the OS environment."""
        self.data["environment_facts"][key] = {
            "value": value,
            "discovered": datetime.now().isoformat()
        }
        self.save()

    def record_tool_usage(self, tool_name: str):
        stats = self.data["performance_stats"]
        stats["tool_usage_counts"][tool_name] = \
            stats["tool_usage_counts"].get(tool_name, 0) + 1

    def record_task_completion(
        self, success: bool, steps: int,
        duration: float = 0, task_type: str = "general"
    ):
        stats = self.data["performance_stats"]
        stats["total_tasks"] += 1
        stats["total_steps"] += steps
        if success:
            stats["successful_tasks"] += 1
        if stats["total_tasks"] > 0:
            stats["avg_steps"] = round(
                stats["total_steps"] / stats["total_tasks"], 1
            )
        if duration > 0:
            if (stats["fastest_task"] is None
                    or duration < stats["fastest_task"]):
                stats["fastest_task"] = round(duration, 1)

        if task_type not in stats["task_type_success"]:
            stats["task_type_success"][task_type] = {
                "attempts": 0, "successes": 0
            }
        stats["task_type_success"][task_type]["attempts"] += 1
        if success:
            stats["task_type_success"][task_type]["successes"] += 1
        self.save()

    def get_relevant_strategies(
        self, goal: str, limit: int = 5
    ) -> list:
        keywords = set(goal.lower().split())
        scored = []
        for s in self.data["learned_strategies"]:
            pattern_words = set(s["pattern"].lower().split())
            overlap = len(keywords & pattern_words)
            if overlap > 0:
                scored.append((overlap, s))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]

    def get_failure_lessons(self, limit: int = 5) -> list:
        return self.data["failure_patterns"][-limit:]

    def get_environment_summary(self) -> str:
        facts = self.data.get("environment_facts", {})
        if not facts:
            return "No environment facts stored yet."
        lines = []
        for k, v in list(facts.items())[-20:]:
            lines.append(f"  {k}: {v['value']}")
        return "\n".join(lines)

    def get_summary(self) -> str:
        stats = self.data["performance_stats"]
        total = stats["total_tasks"]
        success = stats["successful_tasks"]
        rate = round(success / total * 100, 1) if total > 0 else 0
        return (
            f"Tasks: {total} | Success: {rate}% | "
            f"Avg Steps: {stats['avg_steps']} | "
            f"Strategies: {len(self.data['learned_strategies'])} | "
            f"Failures: {len(self.data['failure_patterns'])} | "
            f"Tools Known: {len(self.data['tool_notes'])}"
        )


# ─────────────────────────────────────────────────────
# TASK CLASSIFIER — Understands ANY task type
# ─────────────────────────────────────────────────────
class TaskClassifier:
    """
    Classifies any natural language goal into a task type
    and determines what capabilities are needed.
    """

    TASK_PATTERNS = {
        "gui_automation": [
            "open", "click", "type", "press", "close",
            "minimize", "maximize", "resize", "drag", "scroll",
            "menu", "button", "window", "tab", "dialog"
        ],
        "web_browsing": [
            "search", "browse", "website", "url", "google",
            "download", "chrome", "firefox", "edge", "browser",
            "web", "internet", "http", "navigate", "link"
        ],
        "file_management": [
            "file", "folder", "directory", "copy", "move",
            "delete", "rename", "create", "zip", "extract",
            "archive", "backup", "organize", "sort", "find"
        ],
        "text_editing": [
            "write", "edit", "notepad", "document", "text",
            "word", "paragraph", "content", "draft", "compose"
        ],
        "coding": [
            "code", "program", "script", "python", "javascript",
            "compile", "debug", "function", "class", "algorithm",
            "html", "css", "develop", "build", "run"
        ],
        "system_admin": [
            "install", "uninstall", "update", "service", "process",
            "registry", "permission", "firewall", "network",
            "driver", "config", "setting", "startup", "task manager"
        ],
        "data_processing": [
            "csv", "excel", "spreadsheet", "database", "sql",
            "json", "xml", "parse", "analyze", "convert",
            "transform", "aggregate", "filter", "report"
        ],
        "media": [
            "image", "photo", "video", "audio", "music",
            "screenshot", "record", "play", "resize", "crop",
            "convert", "edit photo", "wallpaper"
        ],
        "communication": [
            "email", "send", "message", "chat", "slack",
            "teams", "outlook", "gmail", "notify", "alert"
        ],
        "research": [
            "find information", "look up", "research", "learn",
            "what is", "how to", "explain", "summarize", "compare"
        ],
    }

    @classmethod
    def classify(cls, goal: str) -> dict:
        """Classify a goal and return task metadata."""
        goal_lower = goal.lower()
        scores = {}

        for task_type, keywords in cls.TASK_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in goal_lower)
            if score > 0:
                scores[task_type] = score

        if not scores:
            primary_type = "general"
        else:
            primary_type = max(scores, key=scores.get)

        # Determine complexity
        word_count = len(goal.split())
        has_multiple_steps = any(
            w in goal_lower
            for w in ["then", "after", "and then", "next",
                       "finally", "also", "first"]
        )
        complexity = (
            "complex" if (word_count > 20 or has_multiple_steps)
            else "medium" if word_count > 10
            else "simple"
        )

        # Determine required capabilities
        required_caps = cls._get_required_capabilities(
            primary_type, goal_lower
        )

        # Estimate steps needed
        step_estimate = (
            30 if complexity == "complex"
            else 15 if complexity == "medium"
            else 8
        )

        return {
            "primary_type": primary_type,
            "all_types": scores,
            "complexity": complexity,
            "required_capabilities": required_caps,
            "estimated_steps": step_estimate,
            "needs_gui": primary_type in [
                "gui_automation", "web_browsing",
                "text_editing", "media"
            ],
            "needs_network": primary_type in [
                "web_browsing", "communication", "research"
            ],
            "is_destructive": any(
                w in goal_lower
                for w in ["delete", "remove", "uninstall",
                           "format", "wipe", "destroy"]
            ),
            "needs_admin": any(
                w in goal_lower
                for w in ["install", "registry", "service",
                           "firewall", "driver", "admin",
                           "permission", "system"]
            ),
        }

    @classmethod
    def _get_required_capabilities(
        cls, task_type: str, goal: str
    ) -> list:
        caps = ["ollama"]  # Always need the LLM

        cap_map = {
            "gui_automation": ["pyautogui", "uiautomation"],
            "web_browsing": ["pyautogui", "uiautomation", "ocr"],
            "file_management": [],
            "text_editing": ["pyautogui"],
            "coding": [],
            "system_admin": [],
            "data_processing": [],
            "media": ["pil"],
            "communication": ["pyautogui", "uiautomation"],
            "research": [],
        }

        caps.extend(cap_map.get(task_type, []))

        if any(w in goal for w in ["screenshot", "screen", "see"]):
            caps.append("pil")
            caps.append("ocr")

        if any(w in goal for w in ["clipboard", "paste", "copy"]):
            caps.append("clipboard")

        return list(set(caps))


# ─────────────────────────────────────────────────────
# TASK DECOMPOSER — Breaks complex goals into steps
# ─────────────────────────────────────────────────────
class TaskDecomposer:
    """
    Uses the LLM to break complex tasks into manageable
    sub-goals with dependencies and verification criteria.
    """

    @staticmethod
    def decompose(
        goal: str, task_info: dict,
        memory: AgentMemory
    ) -> list:
        """Break a goal into ordered sub-tasks."""

        # For simple tasks, don't decompose
        if task_info["complexity"] == "simple":
            return [{"sub_goal": goal, "verify": "Visual confirmation"}]

        # Check memory for known decompositions
        known = memory.data.get("task_decompositions", {})
        for pattern, decomp in known.items():
            if _fuzzy_match(goal, pattern):
                print(c(
                    "  [Decomposer] Using known decomposition pattern.",
                    Colors.CYAN
                ))
                return decomp

        # Ask LLM to decompose
        prompt = f"""Break this task into ordered sub-steps.

TASK: {goal}
TASK TYPE: {task_info['primary_type']}
COMPLEXITY: {task_info['complexity']}

AVAILABLE CAPABILITIES ON THIS SYSTEM:
{json.dumps({k: v for k, v in CAPABILITIES.items() if v}, indent=2)}

OS: {platform.system()} {platform.release()}

Output ONLY a JSON list:
[
  {{
    "sub_goal": "What to do in this step",
    "verify": "How to confirm this step succeeded",
    "depends_on": [0],
    "estimated_actions": 3,
    "fallback": "Alternative approach if this fails"
  }}
]

Keep steps atomic and verifiable. Usually 2-8 steps total."""

        try:
            resp = _call_llm(
                prompt,
                system="You are a task planning expert. Output ONLY valid JSON.",
                timeout=45
            )
            match = re.search(r"\[.*\]", resp, re.DOTALL)
            if match:
                steps = json.loads(match.group(0))
                # Cache decomposition
                memory.data["task_decompositions"][goal[:100]] = steps
                memory.save()
                return steps
        except Exception as e:
            print(c(f"  [Decomposer] Failed: {e}", Colors.YELLOW))

        # Fallback: single step
        return [{"sub_goal": goal, "verify": "Visual confirmation"}]


# ─────────────────────────────────────────────────────
# UNIVERSAL PERCEPTION — Multi-Modal Screen Reading
# ─────────────────────────────────────────────────────
class Perception:
    """
    Multi-modal perception combining:
      - UI Automation tree (structured elements)
      - OCR (text on screen)
      - Pixel analysis (colors, regions)
      - Window enumeration
      - Process awareness
    """

    @staticmethod
    def get_full_context(
        include_ocr: bool = True,
        include_processes: bool = False,
        include_clipboard: bool = False,
        screenshot_path: Optional[str] = None
    ) -> str:
        """Get comprehensive screen context."""
        parts = []

        # 1. System overview
        parts.append(Perception._get_system_state())

        # 2. UI tree
        parts.append(Perception._get_ui_tree())

        # 3. OCR (if enabled and available)
        if include_ocr:
            parts.append(Perception._get_ocr())

        # 4. Active processes (if requested)
        if include_processes:
            parts.append(Perception._get_processes())

        # 5. Clipboard (if requested)
        if include_clipboard:
            parts.append(Perception._get_clipboard())

        # 6. Save screenshot for reference
        if screenshot_path and CAPABILITIES.get("pil"):
            try:
                img = pyautogui.screenshot()
                img.save(screenshot_path)
                parts.append(f"[Screenshot saved: {screenshot_path}]")
            except Exception:
                pass

        return "\n\n".join(filter(None, parts))

    @staticmethod
    def _get_system_state() -> str:
        """Quick system state overview."""
        lines = [
            f"SYSTEM: {platform.system()} {platform.release()}",
            f"TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"SCREEN: {SCREEN_WIDTH}x{SCREEN_HEIGHT}",
        ]

        if CAPABILITIES.get("pyautogui"):
            mx, my = pyautogui.position()
            lines.append(f"MOUSE: ({mx}, {my})")

        return "\n".join(lines)

    @staticmethod
    def _get_ui_tree(
        max_elements: int = 60, max_depth: int = 8
    ) -> str:
        """Get rich UI element tree."""
        if not CAPABILITIES.get("uiautomation"):
            return Perception._get_ui_tree_fallback()

        try:
            active = auto.GetForegroundControl()
            if not active:
                return "[UI Tree] No active window."

            INTERACTIVE = {
                "ButtonControl", "EditControl", "MenuItemControl",
                "TabItemControl", "DocumentControl",
                "HyperlinkControl", "ComboBoxControl",
                "CheckBoxControl", "RadioButtonControl",
                "ListItemControl", "TreeItemControl",
                "TextControl", "ImageControl", "ToolBarControl",
                "StatusBarControl", "MenuBarControl",
                "ScrollBarControl", "SliderControl",
                "SpinnerControl", "ProgressBarControl",
                "DataGridControl", "HeaderControl",
                "GroupControl", "PaneControl",
            }

            lines = [
                f"═══ ACTIVE WINDOW: '{active.Name}' ═══",
                f"    ClassName: {active.ClassName}",
            ]

            try:
                rect = active.BoundingRectangle
                lines.append(
                    f"    Bounds: ({rect.left},{rect.top}) "
                    f"to ({rect.right},{rect.bottom})"
                )
            except Exception:
                pass

            queue = [(active, 0)]
            found = 0

            while queue and found < max_elements:
                ctrl, depth = queue.pop(0)
                if depth > max_depth:
                    continue
                try:
                    children = ctrl.GetChildren()
                    for child in children:
                        queue.append((child, depth + 1))

                        ct = child.ControlTypeName
                        name = child.Name or ""

                        if ct in INTERACTIVE or (name and depth < 4):
                            try:
                                rect = child.BoundingRectangle
                                w = rect.width()
                                h = rect.height()
                                if w <= 0 or h <= 0:
                                    continue
                                cx = (rect.left + rect.right) // 2
                                cy = (rect.top + rect.bottom) // 2

                                indent = "  " * min(depth, 4)
                                extra = ""

                                # Get value for edit controls
                                if ct == "EditControl":
                                    try:
                                        vp = child.GetValuePattern()
                                        if vp:
                                            val = vp.Value[:50]
                                            extra = f' value="{val}"'
                                    except Exception:
                                        pass

                                # Get toggle state
                                if ct in ("CheckBoxControl",
                                          "RadioButtonControl"):
                                    try:
                                        tp = child.GetTogglePattern()
                                        if tp:
                                            extra = (
                                                f" state="
                                                f"{tp.ToggleState}"
                                            )
                                    except Exception:
                                        pass

                                display_name = (
                                    name[:60] if name
                                    else f"[unnamed {ct}]"
                                )
                                lines.append(
                                    f"{indent}[{ct}] "
                                    f"'{display_name}' "
                                    f"@ ({cx},{cy}) "
                                    f"[{w}x{h}]{extra}"
                                )
                                found += 1
                            except Exception:
                                pass
                except Exception:
                    pass

            if found == 0:
                lines.append("  (No interactive elements found)")

            return "\n".join(lines)

        except Exception as e:
            return f"[UI Tree Error] {e}"

    @staticmethod
    def _get_ui_tree_fallback() -> str:
        """Fallback UI detection using win32 API."""
        if not CAPABILITIES.get("win32"):
            return "[UI Tree] uiautomation not available."

        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd)

            lines = [
                f"═══ ACTIVE WINDOW: '{title}' ═══",
                f"    Bounds: {rect}",
            ]

            def enum_callback(child_hwnd, results):
                if win32gui.IsWindowVisible(child_hwnd):
                    text = win32gui.GetWindowText(child_hwnd)
                    cls = win32gui.GetClassName(child_hwnd)
                    r = win32gui.GetWindowRect(child_hwnd)
                    if text or cls:
                        cx = (r[0] + r[2]) // 2
                        cy = (r[1] + r[3]) // 2
                        results.append(
                            f"  [{cls}] '{text}' @ ({cx},{cy})"
                        )

            results = []
            try:
                win32gui.EnumChildWindows(
                    hwnd, enum_callback, results
                )
            except Exception:
                pass

            lines.extend(results[:40])
            return "\n".join(lines)

        except Exception as e:
            return f"[UI Fallback Error] {e}"

    @staticmethod
    def _get_ocr() -> str:
        """Full-screen OCR with position data."""
        if not (CAPABILITIES.get("pyautogui")
                and CAPABILITIES.get("ocr")
                and CAPABILITIES.get("pil")):
            return "[OCR] Required libraries not available."

        try:
            screenshot = pyautogui.screenshot()
            data = pytesseract.image_to_data(
                screenshot, config="--psm 11",
                output_type=pytesseract.Output.DICT
            )

            words = []
            for i, word in enumerate(data["text"]):
                w = word.strip()
                if w and int(data["conf"][i]) > 40 and len(w) > 1:
                    x = data["left"][i] + data["width"][i] // 2
                    y = data["top"][i] + data["height"][i] // 2
                    words.append(f"'{w}' @ ({x},{y})")

            if not words:
                return "[OCR] No text detected on screen."

            return "═══ OCR TEXT ON SCREEN ═══\n" + "\n".join(
                words[:120]
            )

        except Exception as e:
            return f"[OCR Error] {e}"

    @staticmethod
    def _get_processes() -> str:
        """List relevant running processes."""
        if not CAPABILITIES.get("psutil"):
            try:
                result = subprocess.run(
                    "tasklist /FO CSV /NH" if IS_WINDOWS
                    else "ps aux --sort=-pcpu",
                    shell=True, capture_output=True,
                    text=True, timeout=5
                )
                return (
                    "═══ RUNNING PROCESSES ═══\n"
                    + result.stdout[:2000]
                )
            except Exception:
                return "[Processes] Not available."

        try:
            procs = []
            for p in psutil.process_iter(["pid", "name", "status"]):
                info = p.info
                if info["status"] == "running":
                    procs.append(
                        f"  {info['pid']:>6} {info['name']}"
                    )

            return (
                "═══ RUNNING PROCESSES ═══\n"
                + "\n".join(procs[:30])
            )
        except Exception as e:
            return f"[Processes Error] {e}"

    @staticmethod
    def _get_clipboard() -> str:
        if not CAPABILITIES.get("clipboard"):
            return ""
        try:
            text = pyperclip.paste()
            if text:
                return f"═══ CLIPBOARD ═══\n{text[:500]}"
        except Exception:
            pass
        return ""

    @staticmethod
    def wait_for_element(
        name: str, timeout: int = 10,
        interval: float = 0.5
    ) -> Optional[dict]:
        """Wait for a UI element to appear."""
        if not CAPABILITIES.get("uiautomation"):
            time.sleep(timeout / 2)
            return None

        start = time.time()
        name_lower = name.lower()

        while time.time() - start < timeout:
            try:
                active = auto.GetForegroundControl()
                queue = [(active, 0)]
                while queue:
                    ctrl, depth = queue.pop(0)
                    if depth > 5:
                        continue
                    try:
                        for child in ctrl.GetChildren():
                            queue.append((child, depth + 1))
                            if (child.Name
                                    and name_lower
                                    in child.Name.lower()):
                                rect = child.BoundingRectangle
                                return {
                                    "name": child.Name,
                                    "type": child.ControlTypeName,
                                    "x": (rect.left + rect.right) // 2,
                                    "y": (rect.top + rect.bottom) // 2,
                                }
                    except Exception:
                        pass
            except Exception:
                pass

            time.sleep(interval)

        return None

    @staticmethod
    def find_text_on_screen(
        target: str
    ) -> Optional[Tuple[int, int]]:
        """Find text position on screen using OCR."""
        if not (CAPABILITIES.get("pyautogui")
                and CAPABILITIES.get("ocr")):
            return None

        try:
            screenshot = pyautogui.screenshot()
            data = pytesseract.image_to_data(
                screenshot, config="--psm 11",
                output_type=pytesseract.Output.DICT
            )

            target_lower = target.lower()
            for i, word in enumerate(data["text"]):
                if (word.strip().lower()
                        and target_lower in word.strip().lower()
                        and int(data["conf"][i]) > 40):
                    cx = data["left"][i] + data["width"][i] // 2
                    cy = data["top"][i] + data["height"][i] // 2
                    return (cx, cy)
        except Exception:
            pass

        return None


# ─────────────────────────────────────────────────────
# UNIVERSAL ACTION EXECUTOR — Handles ANY action
# ─────────────────────────────────────────────────────
class ActionExecutor:
    """
    Massively expanded action executor that can handle
    virtually any OS operation.
    """

    def __init__(self, safe_mode: bool = False):
        self.safe_mode = safe_mode
        self.action_handlers = self._build_handler_map()

    def _build_handler_map(self) -> dict:
        return {
            # === Mouse Actions ===
            "click": self._click,
            "double_click": self._double_click,
            "right_click": self._right_click,
            "triple_click": self._triple_click,
            "scroll": self._scroll,
            "drag": self._drag,
            "move_mouse": self._move_mouse,
            "click_at_text": self._click_at_text,
            "find_and_click_text": self._find_and_click_text,

            # === Keyboard Actions ===
            "type_text": self._type_text,
            "type_text_fast": self._type_text_fast,
            "press_key": self._press_key,
            "hotkey": self._hotkey,
            "key_combo": self._hotkey,  # alias

            # === Window Management ===
            "list_windows": self._list_windows,
            "focus_window": self._focus_window,
            "close_window": self._close_window,
            "minimize_window": self._minimize_window,
            "maximize_window": self._maximize_window,
            "resize_window": self._resize_window,
            "move_window": self._move_window,
            "snap_window": self._snap_window,
            "switch_window": self._switch_window,
            "new_virtual_desktop": self._new_virtual_desktop,

            # === Application Control ===
            "open_app": self._open_app,
            "close_app": self._close_app,
            "open_url": self._open_url,
            "open_file": self._open_file,
            "start_menu_search": self._start_menu_search,

            # === File Operations ===
            "file_op": self._file_op,
            "find_files": self._find_files,
            "bulk_rename": self._bulk_rename,
            "compress": self._compress,
            "extract": self._extract,
            "get_file_info": self._get_file_info,
            "create_directory": self._create_directory,
            "watch_directory": self._watch_directory,

            # === Clipboard ===
            "clipboard_read": self._clipboard_read,
            "clipboard_write": self._clipboard_write,
            "copy_selection": self._copy_selection,
            "paste": self._paste,
            "select_all": self._select_all,

            # === Shell & Python ===
            "run_shell": self._run_shell,
            "run_powershell": self._run_powershell,
            "run_python": self._run_python,
            "run_python_inline": self._run_python_inline,
            "install_package": self._install_package,

            # === Screen / Perception ===
            "screenshot_ocr": self._screenshot_ocr,
            "screenshot": self._screenshot,
            "get_pixel_color": self._get_pixel_color,
            "find_image": self._find_image,
            "wait_for_text": self._wait_for_text,
            "wait_for_element": self._wait_for_element,

            # === System Operations ===
            "get_system_info": self._get_system_info,
            "list_processes": self._list_processes,
            "kill_process": self._kill_process,
            "set_environment_var": self._set_environment_var,
            "get_environment_var": self._get_environment_var,
            "check_network": self._check_network,
            "get_ip_info": self._get_ip_info,
            "manage_service": self._manage_service,
            "registry_read": self._registry_read,
            "registry_write": self._registry_write,
            "schedule_task": self._schedule_task,

            # === Web / HTTP ===
            "http_request": self._http_request,
            "download_file": self._download_file,
            "scrape_webpage": self._scrape_webpage,

            # === Text & Data Processing ===
            "regex_search": self._regex_search,
            "text_replace": self._text_replace,
            "json_query": self._json_query,
            "csv_query": self._csv_query,

            # === Multi-Step Helpers ===
            "wait": self._wait,
            "conditional_wait": self._conditional_wait,
            "assert_state": self._assert_state,
            "log_message": self._log_message,
            "ask_user": self._ask_user,
            "notify_user": self._notify_user,

            # === Agent Control ===
            "done": self._done,
            "fail": self._fail,
            "sub_goal": self._sub_goal,
            "create_tool": self._create_tool,
            "remember": self._remember,
        }

    def execute(self, action_dict: dict) -> Tuple[bool, str]:
        """Execute any action and return (is_done, observation)."""
        action = action_dict.get("action", "").strip()

        handler = self.action_handlers.get(action)
        if handler is None:
            return False, f"Unknown action: '{action}'. Available: {list(self.action_handlers.keys())}"

        print_action(action, str(action_dict)[:80])

        try:
            is_done, obs = handler(action_dict)
            print_result("error" not in obs.lower(), obs)
            return is_done, obs
        except PermissionError:
            obs = "Permission denied."
        except FileNotFoundError as e:
            obs = f"File not found: {e}"
        except RuntimeError as e:
            obs = f"Runtime error: {e}"
        except subprocess.TimeoutExpired:
            obs = "Command timed out."
        except Exception as e:
            obs = f"Execution error [{type(e).__name__}]: {e}"
            log_event({
                "event": "execution_error",
                "action": action,
                "error": traceback.format_exc()
            })

        print_result(False, obs)
        return False, obs

    def _require(self, cap_name: str):
        if not CAPABILITIES.get(cap_name):
            raise RuntimeError(
                f"Required capability '{cap_name}' is not installed."
            )

    def _confirm(self, prompt: str):
        if self.safe_mode:
            answer = input(
                c(f"\n  [SAFE MODE] {prompt} (y/n): ", Colors.YELLOW)
            ).strip().lower()
            if answer != "y":
                raise RuntimeError(f"User denied: {prompt}")

    # ─── Mouse Actions ───
    def _click(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        x, y = d["x"], d["y"]
        button = d.get("button", "left")
        clicks = d.get("clicks", 1)
        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click(x, y, clicks=clicks, button=button)
        return False, f"Clicked ({x},{y}) button={button} clicks={clicks}"

    def _double_click(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        pyautogui.moveTo(d["x"], d["y"], duration=0.2)
        pyautogui.doubleClick()
        return False, f"Double-clicked ({d['x']},{d['y']})"

    def _right_click(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        pyautogui.moveTo(d["x"], d["y"], duration=0.2)
        pyautogui.rightClick()
        return False, f"Right-clicked ({d['x']},{d['y']})"

    def _triple_click(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        pyautogui.moveTo(d["x"], d["y"], duration=0.2)
        pyautogui.click(clicks=3)
        return False, f"Triple-clicked ({d['x']},{d['y']})"

    def _scroll(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        direction = d.get("direction", "down")
        clicks = d.get("clicks", 3)
        x = d.get("x", SCREEN_WIDTH // 2)
        y = d.get("y", SCREEN_HEIGHT // 2)
        pyautogui.moveTo(x, y)
        amount = clicks if direction == "up" else -clicks
        pyautogui.scroll(amount)
        return False, f"Scrolled {direction} {clicks} clicks at ({x},{y})"

    def _drag(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        pyautogui.moveTo(d["from_x"], d["from_y"], duration=0.2)
        pyautogui.dragTo(
            d["to_x"], d["to_y"],
            duration=d.get("duration", 0.5),
            button=d.get("button", "left")
        )
        return False, (
            f"Dragged ({d['from_x']},{d['from_y']}) "
            f"→ ({d['to_x']},{d['to_y']})"
        )

    def _move_mouse(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        pyautogui.moveTo(d["x"], d["y"], duration=0.2)
        return False, f"Mouse moved to ({d['x']},{d['y']})"

    def _click_at_text(self, d: dict) -> Tuple[bool, str]:
        target = d.get("text", "")
        pos = Perception.find_text_on_screen(target)
        if pos:
            self._require("pyautogui")
            pyautogui.moveTo(pos[0], pos[1], duration=0.25)
            pyautogui.click()
            return False, f"Found and clicked '{target}' at {pos}"
        return False, f"Text '{target}' not found on screen."

    def _find_and_click_text(self, d: dict) -> Tuple[bool, str]:
        return self._click_at_text(d)

    # ─── Keyboard Actions ───
    def _type_text(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        text = d.get("text", "")
        interval = d.get("interval", 0.02)

        # Handle special characters that pyautogui.write can't
        if any(ord(ch) > 127 for ch in text):
            # Use clipboard for unicode text
            if CAPABILITIES.get("clipboard"):
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
                return False, f"Typed (via clipboard): '{text[:60]}'"
            else:
                pyautogui.write(
                    text.encode("ascii", "ignore").decode(),
                    interval=interval
                )
                return False, f"Typed (ASCII only): '{text[:60]}'"

        pyautogui.write(text, interval=interval)
        return False, f"Typed: '{text[:60]}'"

    def _type_text_fast(self, d: dict) -> Tuple[bool, str]:
        """Type text instantly via clipboard."""
        self._require("pyautogui")
        text = d.get("text", "")
        if CAPABILITIES.get("clipboard"):
            old_clip = ""
            try:
                old_clip = pyperclip.paste()
            except Exception:
                pass
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.1)
            try:
                pyperclip.copy(old_clip)
            except Exception:
                pass
            return False, f"Fast-typed: '{text[:60]}'"
        else:
            return self._type_text(d)

    def _press_key(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        key = d.get("key", "").lower()
        times = d.get("times", 1)
        for _ in range(times):
            pyautogui.press(key)
            if times > 1:
                time.sleep(0.05)
        return False, f"Pressed '{key}' x{times}"

    def _hotkey(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        keys = d.get("keys", [])
        pyautogui.hotkey(*keys)
        return False, f"Hotkey: {'+'.join(keys)}"

    # ─── Window Management ───
    def _list_windows(self, d: dict) -> Tuple[bool, str]:
        windows = []

        if CAPABILITIES.get("uiautomation"):
            for w in auto.GetRootControl().GetChildren():
                try:
                    if w.Name and w.BoundingRectangle.width() > 0:
                        windows.append(w.Name)
                except Exception:
                    pass
        elif CAPABILITIES.get("win32"):
            def cb(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        results.append(title)
            win32gui.EnumWindows(cb, windows)
        else:
            try:
                result = subprocess.run(
                    "tasklist /V /FO CSV /NH" if IS_WINDOWS
                    else "wmctrl -l",
                    shell=True, capture_output=True,
                    text=True, timeout=5
                )
                return False, f"Windows:\n{result.stdout[:1500]}"
            except Exception:
                return False, "Cannot list windows."

        if windows:
            return False, (
                f"Open windows ({len(windows)}):\n"
                + "\n".join(f"  • {w}" for w in windows[:30])
            )
        return False, "No windows found."

    def _focus_window(self, d: dict) -> Tuple[bool, str]:
        target = d.get("window_name", "").lower()

        if CAPABILITIES.get("uiautomation"):
            for w in auto.GetRootControl().GetChildren():
                try:
                    if target in w.Name.lower():
                        w.SetFocus()
                        time.sleep(0.5)
                        return False, f"Focused: '{w.Name}'"
                except Exception:
                    pass
        elif CAPABILITIES.get("win32"):
            def cb(hwnd, results):
                if (win32gui.IsWindowVisible(hwnd)
                        and target
                        in win32gui.GetWindowText(hwnd).lower()):
                    results.append(hwnd)

            results = []
            win32gui.EnumWindows(cb, results)
            if results:
                hwnd = results[0]
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.5)
                return False, (
                    f"Focused: "
                    f"'{win32gui.GetWindowText(hwnd)}'"
                )

        # Fallback: Alt+Tab approach
        if CAPABILITIES.get("pyautogui"):
            pyautogui.hotkey("alt", "tab")
            time.sleep(0.5)
            return False, (
                f"Attempted Alt+Tab (direct focus for "
                f"'{target}' not available)"
            )

        return False, f"Window '{target}' not found."

    def _close_window(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        target = d.get("window_name", "")
        if target:
            done, obs = self._focus_window(d)
            time.sleep(0.3)
        pyautogui.hotkey("alt", "F4")
        return False, f"Sent Alt+F4 to close window."

    def _minimize_window(self, d: dict) -> Tuple[bool, str]:
        if CAPABILITIES.get("win32"):
            target = d.get("window_name", "").lower()
            def cb(hwnd, results):
                if (win32gui.IsWindowVisible(hwnd)
                        and target
                        in win32gui.GetWindowText(hwnd).lower()):
                    results.append(hwnd)
            results = []
            win32gui.EnumWindows(cb, results)
            if results:
                win32gui.ShowWindow(results[0], win32con.SW_MINIMIZE)
                return False, "Window minimized."

        if CAPABILITIES.get("pyautogui"):
            pyautogui.hotkey("win", "down")
            return False, "Minimized via Win+Down."

        return False, "Cannot minimize window."

    def _maximize_window(self, d: dict) -> Tuple[bool, str]:
        if CAPABILITIES.get("pyautogui"):
            pyautogui.hotkey("win", "up")
            return False, "Maximized via Win+Up."
        return False, "Cannot maximize window."

    def _resize_window(self, d: dict) -> Tuple[bool, str]:
        if CAPABILITIES.get("win32"):
            target = d.get("window_name", "").lower()
            width = d.get("width", 800)
            height = d.get("height", 600)

            def cb(hwnd, results):
                if (win32gui.IsWindowVisible(hwnd)
                        and target
                        in win32gui.GetWindowText(hwnd).lower()):
                    results.append(hwnd)

            results = []
            win32gui.EnumWindows(cb, results)
            if results:
                win32gui.MoveWindow(
                    results[0], 100, 100, width, height, True
                )
                return False, f"Resized to {width}x{height}."

        return False, "Cannot resize window."

    def _move_window(self, d: dict) -> Tuple[bool, str]:
        if CAPABILITIES.get("win32"):
            target = d.get("window_name", "").lower()
            x = d.get("x", 0)
            y = d.get("y", 0)

            def cb(hwnd, results):
                if (win32gui.IsWindowVisible(hwnd)
                        and target
                        in win32gui.GetWindowText(hwnd).lower()):
                    results.append(hwnd)

            results = []
            win32gui.EnumWindows(cb, results)
            if results:
                rect = win32gui.GetWindowRect(results[0])
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                win32gui.MoveWindow(results[0], x, y, w, h, True)
                return False, f"Moved window to ({x},{y})."

        return False, "Cannot move window."

    def _snap_window(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        direction = d.get("direction", "left")
        key_map = {
            "left": "left", "right": "right",
            "up": "up", "down": "down"
        }
        key = key_map.get(direction, "left")
        pyautogui.hotkey("win", key)
        return False, f"Snapped window {direction}."

    def _switch_window(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        pyautogui.hotkey("alt", "tab")
        time.sleep(0.5)
        return False, "Switched window via Alt+Tab."

    def _new_virtual_desktop(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        pyautogui.hotkey("win", "ctrl", "d")
        return False, "Created new virtual desktop."

    # ─── Application Control ───
    def _open_app(self, d: dict) -> Tuple[bool, str]:
        app = d.get("app", "")

        # Try direct subprocess first
        common_apps = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "powershell": "powershell.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "task manager": "taskmgr.exe",
            "control panel": "control.exe",
            "settings": "ms-settings:",
            "snipping tool": "snippingtool.exe",
            "wordpad": "wordpad.exe",
            "regedit": "regedit.exe",
            "msconfig": "msconfig.exe",
        }

        app_lower = app.lower()
        exe = common_apps.get(app_lower)

        if exe:
            try:
                if exe.endswith(":"):
                    os.startfile(exe)
                else:
                    subprocess.Popen(exe)
                time.sleep(1)
                return False, f"Launched: {exe}"
            except Exception:
                pass

        # Try Start Menu search
        if CAPABILITIES.get("pyautogui"):
            pyautogui.hotkey("win")
            time.sleep(0.8)
            pyautogui.write(app, interval=0.03)
            time.sleep(1)
            pyautogui.press("enter")
            time.sleep(1.5)
            return False, f"Searched and launched: {app}"

        # Fallback: subprocess
        try:
            subprocess.Popen(app, shell=True)
            time.sleep(1)
            return False, f"Launched via shell: {app}"
        except Exception as e:
            return False, f"Failed to open '{app}': {e}"

    def _close_app(self, d: dict) -> Tuple[bool, str]:
        app = d.get("app", "")
        self._confirm(f"Close application: {app}?")

        try:
            if IS_WINDOWS:
                subprocess.run(
                    f"taskkill /IM {app}.exe /F" if "." not in app
                    else f"taskkill /IM {app} /F",
                    shell=True, capture_output=True, timeout=10
                )
            else:
                subprocess.run(
                    f"pkill -f {app}",
                    shell=True, capture_output=True, timeout=10
                )
            return False, f"Closed: {app}"
        except Exception as e:
            return False, f"Failed to close '{app}': {e}"

    def _open_url(self, d: dict) -> Tuple[bool, str]:
        url = d.get("url", "")
        browser = d.get("browser", None)

        if browser:
            try:
                b = webbrowser.get(browser)
                b.open(url)
            except Exception:
                webbrowser.open(url)
        else:
            webbrowser.open(url)

        time.sleep(2)
        return False, f"Opened URL: {url}"

    def _open_file(self, d: dict) -> Tuple[bool, str]:
        path = d.get("path", "")
        try:
            if IS_WINDOWS:
                os.startfile(path)
            elif IS_MAC:
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
            time.sleep(1)
            return False, f"Opened file: {path}"
        except Exception as e:
            return False, f"Failed to open '{path}': {e}"

    def _start_menu_search(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        query = d.get("query", "")
        pyautogui.hotkey("win")
        time.sleep(0.8)
        pyautogui.write(query, interval=0.03)
        time.sleep(1.5)
        return False, f"Start menu search: '{query}'"

    # ─── File Operations ───
    def _file_op(self, d: dict) -> Tuple[bool, str]:
        op = d.get("op", "")
        path = Path(d.get("path", ""))
        dest = (
            Path(d.get("dest", ""))
            if d.get("dest") else None
        )
        content = d.get("content", "")

        if op == "list":
            if not path.exists():
                return False, f"Path does not exist: {path}"
            if path.is_dir():
                items = sorted(path.iterdir())
                lines = []
                for item in items[:80]:
                    try:
                        stat = item.stat()
                        size = stat.st_size
                        mtime = datetime.fromtimestamp(
                            stat.st_mtime
                        ).strftime("%Y-%m-%d %H:%M")
                        kind = "DIR" if item.is_dir() else "FILE"
                        lines.append(
                            f"  [{kind}] {item.name:40} "
                            f"{size:>12,} bytes  {mtime}"
                        )
                    except Exception:
                        lines.append(f"  [?] {item.name}")

                return False, (
                    f"Contents of {path} ({len(items)} items):\n"
                    + "\n".join(lines)
                )
            else:
                stat = path.stat()
                return False, (
                    f"File: {path}\n"
                    f"Size: {stat.st_size:,} bytes\n"
                    f"Modified: {datetime.fromtimestamp(stat.st_mtime)}"
                )

        elif op == "read":
            if not path.exists():
                return False, f"File not found: {path}"
            try:
                text = path.read_text(
                    encoding=d.get("encoding", "utf-8"),
                    errors="replace"
                )
                max_len = d.get("max_length", 3000)
                if len(text) > max_len:
                    return False, (
                        f"File content ({len(text)} chars, "
                        f"showing first {max_len}):\n"
                        + text[:max_len]
                    )
                return False, f"File content:\n{text}"
            except Exception as e:
                return False, f"Read error: {e}"

        elif op == "read_binary":
            if not path.exists():
                return False, f"File not found: {path}"
            data = path.read_bytes()
            return False, (
                f"Binary file: {len(data)} bytes, "
                f"first 100 hex: {data[:100].hex()}"
            )

        elif op == "write":
            self._confirm(f"Write to {path}?")
            path.parent.mkdir(parents=True, exist_ok=True)
            encoding = d.get("encoding", "utf-8")
            mode = d.get("mode", "w")
            with open(path, mode, encoding=encoding) as f:
                f.write(content)
            return False, f"Written {len(content)} chars to {path}"

        elif op == "append":
            self._confirm(f"Append to {path}?")
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)
            return False, f"Appended {len(content)} chars to {path}"

        elif op == "copy":
            self._confirm(f"Copy {path} → {dest}?")
            if path.is_dir():
                shutil.copytree(str(path), str(dest))
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(path), str(dest))
            return False, f"Copied: {path} → {dest}"

        elif op == "move":
            self._confirm(f"Move {path} → {dest}?")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(dest))
            return False, f"Moved: {path} → {dest}"

        elif op == "rename":
            new_name = d.get("new_name", "")
            self._confirm(f"Rename {path} → {new_name}?")
            new_path = path.parent / new_name
            path.rename(new_path)
            return False, f"Renamed: {path.name} → {new_name}"

        elif op == "delete":
            self._confirm(f"DELETE {path}?")
            if path.is_dir():
                shutil.rmtree(str(path))
            elif path.exists():
                path.unlink()
            else:
                return False, f"Not found: {path}"
            return False, f"Deleted: {path}"

        elif op == "exists":
            exists = path.exists()
            return False, (
                f"{'Exists' if exists else 'Does not exist'}: {path}"
            )

        elif op == "tree":
            if not path.exists() or not path.is_dir():
                return False, f"Not a directory: {path}"
            lines = []
            max_items = d.get("max_items", 100)
            count = 0
            for root, dirs, files in os.walk(path):
                level = root.replace(str(path), "").count(os.sep)
                indent = "  " * level
                lines.append(f"{indent}{os.path.basename(root)}/")
                count += 1
                sub_indent = "  " * (level + 1)
                for f in files[:20]:
                    lines.append(f"{sub_indent}{f}")
                    count += 1
                if count >= max_items:
                    lines.append("... (truncated)")
                    break
            return False, f"Directory tree:\n" + "\n".join(lines)

        else:
            return False, f"Unknown file_op: {op}"

    def _find_files(self, d: dict) -> Tuple[bool, str]:
        pattern = d.get("pattern", "*")
        search_path = d.get("path", ".")
        recursive = d.get("recursive", True)
        max_results = d.get("max_results", 50)

        results = []
        try:
            if recursive:
                for root, dirs, files in os.walk(search_path):
                    for f in files:
                        if fnmatch.fnmatch(f.lower(), pattern.lower()):
                            results.append(os.path.join(root, f))
                            if len(results) >= max_results:
                                break
                    if len(results) >= max_results:
                        break
            else:
                results = glob.glob(
                    os.path.join(search_path, pattern)
                )[:max_results]

            return False, (
                f"Found {len(results)} files matching '{pattern}':\n"
                + "\n".join(f"  {r}" for r in results)
            )
        except Exception as e:
            return False, f"Search error: {e}"

    def _bulk_rename(self, d: dict) -> Tuple[bool, str]:
        path = Path(d.get("path", "."))
        pattern = d.get("pattern", "*")
        find = d.get("find", "")
        replace = d.get("replace", "")
        self._confirm(
            f"Bulk rename in {path}: "
            f"'{find}' → '{replace}'?"
        )

        renamed = 0
        for item in path.iterdir():
            if fnmatch.fnmatch(item.name, pattern):
                new_name = item.name.replace(find, replace)
                if new_name != item.name:
                    item.rename(item.parent / new_name)
                    renamed += 1

        return False, f"Renamed {renamed} files."

    def _compress(self, d: dict) -> Tuple[bool, str]:
        path = d.get("path", "")
        output = d.get("output", f"{path}.zip")
        fmt = d.get("format", "zip")

        try:
            shutil.make_archive(
                output.replace(f".{fmt}", ""),
                fmt, path
            )
            return False, f"Compressed: {path} → {output}"
        except Exception as e:
            return False, f"Compression error: {e}"

    def _extract(self, d: dict) -> Tuple[bool, str]:
        path = d.get("path", "")
        dest = d.get("dest", ".")

        try:
            shutil.unpack_archive(path, dest)
            return False, f"Extracted: {path} → {dest}"
        except Exception as e:
            return False, f"Extraction error: {e}"

    def _get_file_info(self, d: dict) -> Tuple[bool, str]:
        path = Path(d.get("path", ""))
        if not path.exists():
            return False, f"Not found: {path}"

        stat = path.stat()
        info = {
            "path": str(path.absolute()),
            "name": path.name,
            "extension": path.suffix,
            "size_bytes": stat.st_size,
            "size_human": _human_size(stat.st_size),
            "created": datetime.fromtimestamp(
                stat.st_ctime
            ).isoformat(),
            "modified": datetime.fromtimestamp(
                stat.st_mtime
            ).isoformat(),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "is_symlink": path.is_symlink(),
        }
        return False, json.dumps(info, indent=2)

    def _create_directory(self, d: dict) -> Tuple[bool, str]:
        path = Path(d.get("path", ""))
        path.mkdir(parents=True, exist_ok=True)
        return False, f"Directory created: {path}"

    def _watch_directory(self, d: dict) -> Tuple[bool, str]:
        """Take a snapshot of directory state."""
        path = Path(d.get("path", "."))
        if not path.is_dir():
            return False, f"Not a directory: {path}"

        items = {}
        for item in path.iterdir():
            try:
                stat = item.stat()
                items[str(item)] = {
                    "size": stat.st_size,
                    "mtime": stat.st_mtime
                }
            except Exception:
                pass

        return False, (
            f"Directory snapshot ({len(items)} items): "
            + json.dumps(items, indent=2)[:2000]
        )

    # ─── Clipboard ───
    def _clipboard_read(self, d: dict) -> Tuple[bool, str]:
        self._require("clipboard")
        text = pyperclip.paste()
        return False, f"Clipboard content: {repr(text[:500])}"

    def _clipboard_write(self, d: dict) -> Tuple[bool, str]:
        self._require("clipboard")
        pyperclip.copy(d.get("text", ""))
        return False, "Clipboard updated."

    def _copy_selection(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.3)
        if CAPABILITIES.get("clipboard"):
            text = pyperclip.paste()
            return False, f"Copied: {repr(text[:200])}"
        return False, "Copied selection to clipboard."

    def _paste(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        pyautogui.hotkey("ctrl", "v")
        return False, "Pasted from clipboard."

    def _select_all(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        pyautogui.hotkey("ctrl", "a")
        return False, "Selected all."

    # ─── Shell & Python ───
    def _run_shell(self, d: dict) -> Tuple[bool, str]:
        cmd = d.get("cmd", "")
        timeout = d.get("timeout", 30)
        self._confirm(f"Run shell: {cmd}")

        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=timeout,
            cwd=d.get("cwd", None)
        )

        output = result.stdout or ""
        error = result.stderr or ""
        code = result.returncode

        obs = f"Exit code: {code}\n"
        if output:
            obs += f"STDOUT:\n{output[:2000]}\n"
        if error:
            obs += f"STDERR:\n{error[:1000]}"

        return False, obs.strip()

    def _run_powershell(self, d: dict) -> Tuple[bool, str]:
        cmd = d.get("cmd", "")
        timeout = d.get("timeout", 30)
        self._confirm(f"Run PowerShell: {cmd}")

        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout
        )

        output = result.stdout or result.stderr or "No output."
        return False, f"PowerShell (exit {result.returncode}):\n{output[:2000]}"

    def _run_python(self, d: dict) -> Tuple[bool, str]:
        code = d.get("code", "")

        print(c("\n  ─── PYTHON CODE TO EXECUTE ───", Colors.YELLOW))
        for line in code.split("\n"):
            print(c(f"  │ {line}", Colors.DIM))
        print(c("  ─────────────────────────────\n", Colors.YELLOW))

        if self.safe_mode:
            if input("  Allow Python execution? (y/n): "
                      ).strip().lower() != "y":
                return False, "User denied Python execution."

        script_path = Path(WORKSPACE) / f"script_{int(time.time())}.py"
        script_path.write_text(code, encoding="utf-8")

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True, text=True,
                timeout=d.get("timeout", 30),
                cwd=d.get("cwd", None)
            )

            if result.returncode == 0:
                return False, (
                    f"Python output:\n{result.stdout[:2000]}"
                )
            else:
                return False, (
                    f"Python error (exit {result.returncode}):\n"
                    f"{result.stderr[:2000]}"
                )
        finally:
            try:
                script_path.unlink()
            except Exception:
                pass

    def _run_python_inline(self, d: dict) -> Tuple[bool, str]:
        """Execute Python code in-process (fast but less isolated)."""
        code = d.get("code", "")

        if self.safe_mode:
            print(c(f"  Code: {code[:200]}", Colors.YELLOW))
            if input("  Allow inline Python? (y/n): "
                      ).strip().lower() != "y":
                return False, "User denied."

        stdout_capture = StringIO()
        stderr_capture = StringIO()
        local_vars = {}

        try:
            with redirect_stdout(stdout_capture), \
                 redirect_stderr(stderr_capture):
                exec(code, {"__builtins__": __builtins__}, local_vars)

            output = stdout_capture.getvalue()
            errors = stderr_capture.getvalue()

            result = ""
            if output:
                result += f"Output:\n{output[:2000]}\n"
            if errors:
                result += f"Stderr:\n{errors[:500]}\n"
            if "result" in local_vars:
                result += f"Result: {str(local_vars['result'])[:500]}"

            return False, result or "Executed successfully (no output)."

        except Exception as e:
            return False, f"Python error: {e}"

    def _install_package(self, d: dict) -> Tuple[bool, str]:
        package = d.get("package", "")
        self._confirm(f"Install pip package: {package}")

        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True, text=True, timeout=120
        )

        if result.returncode == 0:
            return False, f"Installed: {package}"
        return False, f"Install failed: {result.stderr[:500]}"

    # ─── Screen / Perception ───
    def _screenshot_ocr(self, d: dict) -> Tuple[bool, str]:
        return False, Perception._get_ocr()

    def _screenshot(self, d: dict) -> Tuple[bool, str]:
        if not CAPABILITIES.get("pil"):
            return False, "PIL not available for screenshots."

        filename = d.get(
            "filename",
            f"screenshot_{int(time.time())}.png"
        )
        path = Path(SCREENSHOTS_DIR) / filename

        try:
            img = pyautogui.screenshot()
            # Optionally crop to region
            region = d.get("region")
            if region:
                img = img.crop((
                    region["x"], region["y"],
                    region["x"] + region["width"],
                    region["y"] + region["height"]
                ))
            img.save(str(path))
            return False, f"Screenshot saved: {path}"
        except Exception as e:
            return False, f"Screenshot error: {e}"

    def _get_pixel_color(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        x, y = d["x"], d["y"]
        try:
            color = pyautogui.pixel(x, y)
            return False, (
                f"Pixel at ({x},{y}): "
                f"RGB({color[0]},{color[1]},{color[2]}) "
                f"Hex: #{color[0]:02x}{color[1]:02x}{color[2]:02x}"
            )
        except Exception as e:
            return False, f"Pixel read error: {e}"

    def _find_image(self, d: dict) -> Tuple[bool, str]:
        self._require("pyautogui")
        image_path = d.get("image", "")
        confidence = d.get("confidence", 0.8)

        try:
            location = pyautogui.locateOnScreen(
                image_path, confidence=confidence
            )
            if location:
                cx = location.left + location.width // 2
                cy = location.top + location.height // 2
                return False, (
                    f"Image found at ({cx},{cy}) "
                    f"[{location.width}x{location.height}]"
                )
            return False, "Image not found on screen."
        except Exception as e:
            return False, f"Image search error: {e}"

    def _wait_for_text(self, d: dict) -> Tuple[bool, str]:
        target = d.get("text", "")
        timeout = d.get("timeout", 10)
        start = time.time()

        while time.time() - start < timeout:
            pos = Perception.find_text_on_screen(target)
            if pos:
                return False, (
                    f"Text '{target}' appeared at {pos} "
                    f"after {time.time()-start:.1f}s"
                )
            time.sleep(0.5)

        return False, (
            f"Text '{target}' not found within {timeout}s."
        )

    def _wait_for_element(self, d: dict) -> Tuple[bool, str]:
        name = d.get("name", "")
        timeout = d.get("timeout", 10)

        result = Perception.wait_for_element(name, timeout)
        if result:
            return False, (
                f"Element '{name}' found: "
                f"{result['type']} at ({result['x']},{result['y']})"
            )
        return False, (
            f"Element '{name}' not found within {timeout}s."
        )

    # ─── System Operations ───
    def _get_system_info(self, d: dict) -> Tuple[bool, str]:
        info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.architecture(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": socket.gethostname(),
            "python_version": sys.version,
            "screen_size": f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}",
            "cwd": os.getcwd(),
            "home": str(Path.home()),
            "username": os.getenv("USERNAME") or os.getenv("USER"),
        }

        if CAPABILITIES.get("psutil"):
            info["cpu_count"] = psutil.cpu_count()
            info["cpu_percent"] = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            info["ram_total"] = _human_size(mem.total)
            info["ram_available"] = _human_size(mem.available)
            info["ram_percent"] = mem.percent
            disk = psutil.disk_usage("/")
            info["disk_total"] = _human_size(disk.total)
            info["disk_free"] = _human_size(disk.free)

        return False, (
            "System Information:\n"
            + json.dumps(info, indent=2, default=str)
        )

    def _list_processes(self, d: dict) -> Tuple[bool, str]:
        return False, Perception._get_processes()

    def _kill_process(self, d: dict) -> Tuple[bool, str]:
        target = d.get("name", d.get("pid", ""))
        self._confirm(f"Kill process: {target}")

        if isinstance(target, int) or target.isdigit():
            pid = int(target)
            try:
                if CAPABILITIES.get("psutil"):
                    p = psutil.Process(pid)
                    p.terminate()
                else:
                    os.kill(pid, signal.SIGTERM)
                return False, f"Killed process PID {pid}."
            except Exception as e:
                return False, f"Kill failed: {e}"
        else:
            cmd = (
                f"taskkill /IM {target} /F" if IS_WINDOWS
                else f"pkill -f {target}"
            )
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True
            )
            return False, (
                result.stdout or result.stderr or
                f"Attempted to kill: {target}"
            )

    def _set_environment_var(self, d: dict) -> Tuple[bool, str]:
        name = d.get("name", "")
        value = d.get("value", "")
        permanent = d.get("permanent", False)

        os.environ[name] = value

        if permanent and IS_WINDOWS:
            self._confirm(
                f"Set permanent env var: {name}={value}"
            )
            subprocess.run(
                f'setx {name} "{value}"',
                shell=True, capture_output=True
            )

        return False, f"Environment variable set: {name}={value}"

    def _get_environment_var(self, d: dict) -> Tuple[bool, str]:
        name = d.get("name", "")
        value = os.environ.get(name, "(not set)")
        return False, f"{name} = {value}"

    def _check_network(self, d: dict) -> Tuple[bool, str]:
        host = d.get("host", "8.8.8.8")
        port = d.get("port", 53)
        timeout = d.get("timeout", 3)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.close()
            return False, f"Network OK: {host}:{port} reachable."
        except Exception as e:
            return False, f"Network error: {host}:{port} - {e}"

    def _get_ip_info(self, d: dict) -> Tuple[bool, str]:
        info = {"hostname": socket.gethostname()}

        try:
            info["local_ip"] = socket.gethostbyname(
                socket.gethostname()
            )
        except Exception:
            info["local_ip"] = "unknown"

        try:
            resp = requests.get(
                "https://api.ipify.org?format=json", timeout=5
            )
            info["public_ip"] = resp.json().get("ip", "unknown")
        except Exception:
            info["public_ip"] = "unavailable"

        return False, json.dumps(info, indent=2)

    def _manage_service(self, d: dict) -> Tuple[bool, str]:
        service = d.get("service", "")
        action_type = d.get("op", "status")
        self._confirm(f"Service {action_type}: {service}")

        if IS_WINDOWS:
            cmd = f"sc {action_type} {service}"
        else:
            cmd = f"systemctl {action_type} {service}"

        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=15
        )
        return False, (
            result.stdout or result.stderr or
            f"Service {action_type}: {service}"
        )

    def _registry_read(self, d: dict) -> Tuple[bool, str]:
        if not IS_WINDOWS:
            return False, "Registry is Windows-only."

        key_path = d.get("key", "")
        value_name = d.get("value", "")

        hive_map = {
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKCU": winreg.HKEY_CURRENT_USER,
            "HKCR": winreg.HKEY_CLASSES_ROOT,
        }

        parts = key_path.split("\\", 1)
        hive = hive_map.get(parts[0], winreg.HKEY_CURRENT_USER)
        subkey = parts[1] if len(parts) > 1 else ""

        try:
            with winreg.OpenKey(hive, subkey) as key:
                if value_name:
                    val, type_ = winreg.QueryValueEx(key, value_name)
                    return False, f"Registry: {value_name} = {val}"
                else:
                    # List values
                    values = []
                    i = 0
                    while True:
                        try:
                            name, val, type_ = winreg.EnumValue(key, i)
                            values.append(f"  {name} = {val}")
                            i += 1
                        except WindowsError:
                            break
                    return False, (
                        f"Registry values in {key_path}:\n"
                        + "\n".join(values[:30])
                    )
        except Exception as e:
            return False, f"Registry error: {e}"

    def _registry_write(self, d: dict) -> Tuple[bool, str]:
        if not IS_WINDOWS:
            return False, "Registry is Windows-only."

        self._confirm(f"Write to registry: {d.get('key', '')}")

        key_path = d.get("key", "")
        value_name = d.get("value", "")
        data = d.get("data", "")

        hive_map = {
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKCU": winreg.HKEY_CURRENT_USER,
        }

        parts = key_path.split("\\", 1)
        hive = hive_map.get(parts[0], winreg.HKEY_CURRENT_USER)
        subkey = parts[1] if len(parts) > 1 else ""

        try:
            with winreg.OpenKey(
                hive, subkey, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.SetValueEx(
                    key, value_name, 0, winreg.REG_SZ, str(data)
                )
                return False, (
                    f"Registry written: {value_name} = {data}"
                )
        except Exception as e:
            return False, f"Registry write error: {e}"

    def _schedule_task(self, d: dict) -> Tuple[bool, str]:
        if not IS_WINDOWS:
            return False, "Task scheduling via schtasks is Windows-only."

        name = d.get("name", "AgentTask")
        cmd = d.get("cmd", "")
        schedule = d.get("schedule", "ONCE")
        time_str = d.get("time", "12:00")

        self._confirm(f"Schedule task: {name} → {cmd}")

        schtasks_cmd = (
            f'schtasks /CREATE /TN "{name}" /TR "{cmd}" '
            f'/SC {schedule} /ST {time_str} /F'
        )

        result = subprocess.run(
            schtasks_cmd, shell=True,
            capture_output=True, text=True
        )
        return False, (
            result.stdout or result.stderr or
            f"Task scheduled: {name}"
        )

    # ─── Web / HTTP ───
    def _http_request(self, d: dict) -> Tuple[bool, str]:
        url = d.get("url", "")
        method = d.get("method", "GET").upper()
        headers = d.get("headers", {})
        body = d.get("body", None)
        timeout = d.get("timeout", 15)

        try:
            resp = requests.request(
                method, url, headers=headers,
                json=body if isinstance(body, dict) else None,
                data=body if isinstance(body, str) else None,
                timeout=timeout
            )

            result = {
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "body": resp.text[:3000]
            }

            return False, json.dumps(result, indent=2)

        except Exception as e:
            return False, f"HTTP error: {e}"

    def _download_file(self, d: dict) -> Tuple[bool, str]:
        url = d.get("url", "")
        dest = d.get("dest", "")
        if not dest:
            filename = url.split("/")[-1].split("?")[0] or "download"
            dest = str(Path(WORKSPACE) / filename)

        self._confirm(f"Download {url} → {dest}")

        try:
            resp = requests.get(url, stream=True, timeout=60)
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)

            return False, (
                f"Downloaded: {dest} "
                f"({_human_size(downloaded)})"
            )
        except Exception as e:
            return False, f"Download error: {e}"

    def _scrape_webpage(self, d: dict) -> Tuple[bool, str]:
        url = d.get("url", "")
        selector = d.get("selector", None)

        try:
            resp = requests.get(
                url, timeout=15,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    )
                }
            )

            if CAPABILITIES.get("beautifulsoup"):
                soup = BeautifulSoup(resp.text, "html.parser")

                # Remove scripts and styles
                for tag in soup(["script", "style"]):
                    tag.decompose()

                if selector:
                    elements = soup.select(selector)
                    text = "\n".join(
                        el.get_text(strip=True)
                        for el in elements[:20]
                    )
                else:
                    text = soup.get_text(
                        separator="\n", strip=True
                    )

                return False, f"Webpage content:\n{text[:3000]}"
            else:
                # Basic text extraction
                text = re.sub(r"<[^>]+>", " ", resp.text)
                text = re.sub(r"\s+", " ", text).strip()
                return False, f"Webpage (raw):\n{text[:3000]}"

        except Exception as e:
            return False, f"Scrape error: {e}"

    # ─── Text & Data Processing ───
    def _regex_search(self, d: dict) -> Tuple[bool, str]:
        text = d.get("text", "")
        pattern = d.get("pattern", "")
        flags = re.IGNORECASE if d.get("ignore_case") else 0

        matches = re.findall(pattern, text, flags)
        return False, (
            f"Found {len(matches)} matches: "
            + json.dumps(matches[:50])
        )

    def _text_replace(self, d: dict) -> Tuple[bool, str]:
        path = Path(d.get("path", ""))
        find = d.get("find", "")
        replace = d.get("replace", "")

        if not path.exists():
            return False, f"File not found: {path}"

        self._confirm(
            f"Replace '{find}' with '{replace}' in {path}"
        )

        text = path.read_text(encoding="utf-8")
        count = text.count(find)
        new_text = text.replace(find, replace)
        path.write_text(new_text, encoding="utf-8")

        return False, (
            f"Replaced {count} occurrences in {path}."
        )

    def _json_query(self, d: dict) -> Tuple[bool, str]:
        source = d.get("source", "")
        query = d.get("query", "")

        # Load JSON from file or string
        if Path(source).exists():
            with open(source, "r") as f:
                data = json.load(f)
        else:
            data = json.loads(source)

        # Simple dot-notation query
        result = data
        for key in query.split("."):
            if key.isdigit():
                result = result[int(key)]
            elif key:
                result = result[key]

        return False, f"Query result:\n{json.dumps(result, indent=2, default=str)[:2000]}"

    def _csv_query(self, d: dict) -> Tuple[bool, str]:
        path = d.get("path", "")
        action_type = d.get("op", "read")

        import csv

        if action_type == "read":
            rows = []
            with open(path, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    rows.append(row)
                    if i > 50:
                        break

            return False, (
                f"CSV ({len(rows)} rows):\n"
                + "\n".join(
                    ", ".join(r[:10]) for r in rows[:30]
                )
            )

        elif action_type == "headers":
            with open(path, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)
            return False, f"CSV headers: {headers}"

        return False, f"Unknown CSV op: {action_type}"

    # ─── Multi-Step Helpers ───
    def _wait(self, d: dict) -> Tuple[bool, str]:
        secs = max(0.5, float(d.get("seconds", 2)))
        time.sleep(secs)
        return False, f"Waited {secs}s."

    def _conditional_wait(self, d: dict) -> Tuple[bool, str]:
        """Wait until a condition is met."""
        condition = d.get("condition", "text_visible")
        target = d.get("target", "")
        timeout = d.get("timeout", 15)

        if condition == "text_visible":
            return self._wait_for_text(d)
        elif condition == "element_visible":
            return self._wait_for_element(
                {"name": target, "timeout": timeout}
            )
        elif condition == "file_exists":
            start = time.time()
            while time.time() - start < timeout:
                if Path(target).exists():
                    return False, f"File appeared: {target}"
                time.sleep(0.5)
            return False, f"File '{target}' didn't appear within {timeout}s."
        elif condition == "process_running":
            start = time.time()
            while time.time() - start < timeout:
                try:
                    result = subprocess.run(
                        f'tasklist /FI "IMAGENAME eq {target}" /NH'
                        if IS_WINDOWS else f"pgrep -f {target}",
                        shell=True, capture_output=True, text=True
                    )
                    if target.lower() in result.stdout.lower():
                        return False, f"Process '{target}' is running."
                except Exception:
                    pass
                time.sleep(0.5)
            return False, f"Process '{target}' not found within {timeout}s."

        return False, f"Unknown condition: {condition}"

    def _assert_state(self, d: dict) -> Tuple[bool, str]:
        """Assert something about the current state."""
        assertion = d.get("assertion", "")
        expected = d.get("expected", "")

        if assertion == "window_title":
            if CAPABILITIES.get("uiautomation"):
                active = auto.GetForegroundControl()
                actual = active.Name if active else ""
            elif CAPABILITIES.get("win32"):
                hwnd = win32gui.GetForegroundWindow()
                actual = win32gui.GetWindowText(hwnd)
            else:
                actual = "(unknown)"

            match = expected.lower() in actual.lower()
            return False, (
                f"Window title assertion: "
                f"expected='{expected}', actual='{actual}', "
                f"match={match}"
            )

        elif assertion == "file_exists":
            exists = Path(expected).exists()
            return False, (
                f"File exists assertion: {expected} → {exists}"
            )

        elif assertion == "text_on_screen":
            pos = Perception.find_text_on_screen(expected)
            return False, (
                f"Text on screen assertion: '{expected}' → "
                f"{'Found at ' + str(pos) if pos else 'Not found'}"
            )

        return False, f"Unknown assertion: {assertion}"

    def _log_message(self, d: dict) -> Tuple[bool, str]:
        msg = d.get("message", "")
        level = d.get("level", "info")
        log_event({"event": "agent_log", "level": level, "message": msg})
        return False, f"Logged [{level}]: {msg}"

    def _ask_user(self, d: dict) -> Tuple[bool, str]:
        question = d.get("question", "")
        options = d.get("options", [])

        prompt = f"\n  [Agent asks] {question}"
        if options:
            prompt += "\n  Options: " + ", ".join(options)
        prompt += "\n  Your answer: "

        answer = input(c(prompt, Colors.CYAN)).strip()
        return False, f"User answered: {answer}"

    def _notify_user(self, d: dict) -> Tuple[bool, str]:
        message = d.get("message", "")
        title = d.get("title", "Agent Notification")

        # Try system notification
        if IS_WINDOWS:
            try:
                from ctypes import windll
                windll.user32.MessageBoxW(
                    0, message, title, 0x40
                )
                return False, f"Notification shown: {message}"
            except Exception:
                pass

        # Fallback: print prominently
        banner(f"📢 {title}: {message}", char="★")
        return False, f"Notification: {message}"

    # ─── Agent Control ───
    def _done(self, d: dict) -> Tuple[bool, str]:
        msg = d.get("message", "Task complete.")
        banner(f"✓ DONE: {msg}", char="═", color=Colors.GREEN)
        return True, msg

    def _fail(self, d: dict) -> Tuple[bool, str]:
        reason = d.get("reason", "Task failed.")
        banner(f"✗ FAILED: {reason}", char="═", color=Colors.RED)
        return True, f"FAILED: {reason}"

    def _sub_goal(self, d: dict) -> Tuple[bool, str]:
        """Set a sub-goal for focused attention."""
        sub = d.get("goal", "")
        return False, f"Sub-goal set: {sub}"

    def _create_tool(self, d: dict) -> Tuple[bool, str]:
        """Dynamically create a new tool."""
        name = d.get("name", "")
        code = d.get("code", "")
        description = d.get("description", "")

        if not name or not code:
            return False, "Tool creation requires 'name' and 'code'."

        tool_path = Path(DYNAMIC_TOOLS_DIR) / f"{name}.py"
        tool_path.write_text(code, encoding="utf-8")

        return False, (
            f"Dynamic tool created: {name} "
            f"({description})"
        )

    def _remember(self, d: dict) -> Tuple[bool, str]:
        """Store a fact in agent memory."""
        key = d.get("key", "")
        value = d.get("value", "")
        memory = AgentMemory()
        memory.add_environment_fact(key, value)
        return False, f"Remembered: {key} = {value}"


# ─────────────────────────────────────────────────────
# BRAIN — Enhanced LLM Interface with Memory
# ─────────────────────────────────────────────────────
def _call_llm(
    prompt: str, system: str = "",
    timeout: int = 60
) -> str:
    """Raw LLM call with retry logic."""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system,
        "stream": False
    }

    for attempt in range(3):
        try:
            resp = requests.post(
                OLLAMA_URL, json=payload,
                timeout=timeout
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except requests.exceptions.Timeout:
            if attempt < 2:
                print(c(
                    f"  [LLM] Timeout, retrying "
                    f"({attempt + 1}/3)...",
                    Colors.YELLOW
                ))
                time.sleep(2 ** attempt)
            else:
                raise
        except requests.exceptions.ConnectionError:
            print(c(
                "  [LLM] Cannot connect to Ollama. "
                "Is it running?",
                Colors.RED
            ))
            raise

    return ""


def _build_system_prompt(
    task_info: dict, capabilities_summary: str
) -> str:
    """Build a dynamic system prompt based on task type."""

    # Get all available action names
    executor = ActionExecutor()
    all_actions = sorted(executor.action_handlers.keys())

    return f"""You are an elite autonomous OS agent that can do ANY task.
Your ONLY job is to achieve the user's goal through reasoning and actions.

══ ABSOLUTE OUTPUT RULES ══
• Output EXACTLY ONE raw JSON object — no markdown, no explanation, no extra text.
• "action_command" must be a single {{}} dict, NEVER a [] list.
• If an action failed, DO NOT retry identically — change strategy.
• Think step by step. Be precise with coordinates and paths.

══ TASK CONTEXT ══
Task Type: {task_info.get('primary_type', 'general')}
Complexity: {task_info.get('complexity', 'unknown')}
OS: {platform.system()} {platform.release()}
Screen: {SCREEN_WIDTH}x{SCREEN_HEIGHT}
Available Capabilities: {capabilities_summary}

══ ALL AVAILABLE ACTIONS ══
{_format_action_reference(all_actions)}

══ REQUIRED OUTPUT FORMAT ══
{{
  "thought": "My reasoning: what I observe, what I'll do next and why.",
  "action_command": {{ "action": "action_name", ...params... }},
  "confidence": 0.0-1.0,
  "sub_goal": "Current sub-goal I'm working on"
}}

══ STRATEGY GUIDELINES ══
• For GUI tasks: Use UI tree elements first, fall back to OCR, then coordinates.
• For file tasks: Use file_op with absolute paths when possible.
• For web tasks: open_url first, then interact via GUI or scrape_webpage.
• For coding: Use run_python or run_shell.
• For system tasks: Use run_shell, run_powershell, or specific system actions.
• Always verify your actions had the expected effect.
• When stuck, try: screenshot_ocr, list_windows, get_system_info.
• Use "done" when the goal is fully achieved.
• Use "fail" only when you're certain the task cannot be completed.
"""


def _format_action_reference(actions: list) -> str:
    """Format action names into a compact reference."""

    # Group actions by category
    categories = {
        "Mouse": ["click", "double_click", "right_click",
                   "triple_click", "scroll", "drag",
                   "move_mouse", "click_at_text",
                   "find_and_click_text"],
        "Keyboard": ["type_text", "type_text_fast",
                      "press_key", "hotkey"],
        "Window": ["list_windows", "focus_window",
                    "close_window", "minimize_window",
                    "maximize_window", "resize_window",
                    "move_window", "snap_window",
                    "switch_window"],
        "App": ["open_app", "close_app", "open_url",
                "open_file", "start_menu_search"],
        "File": ["file_op", "find_files", "bulk_rename",
                 "compress", "extract", "get_file_info",
                 "create_directory"],
        "Clipboard": ["clipboard_read", "clipboard_write",
                       "copy_selection", "paste", "select_all"],
        "Shell": ["run_shell", "run_powershell",
                  "run_python", "run_python_inline",
                  "install_package"],
        "Screen": ["screenshot_ocr", "screenshot",
                   "get_pixel_color", "find_image",
                   "wait_for_text", "wait_for_element"],
        "System": ["get_system_info", "list_processes",
                   "kill_process", "set_environment_var",
                   "get_environment_var", "check_network",
                   "get_ip_info", "manage_service",
                   "registry_read", "registry_write",
                   "schedule_task"],
        "Web": ["http_request", "download_file",
                "scrape_webpage"],
        "Data": ["regex_search", "text_replace",
                 "json_query", "csv_query"],
        "Flow": ["wait", "conditional_wait", "assert_state",
                 "log_message", "ask_user", "notify_user"],
        "Control": ["done", "fail", "sub_goal",
                    "create_tool", "remember"],
    }

    lines = []
    for cat, acts in categories.items():
        available = [a for a in acts if a in actions]
        if available:
            lines.append(f"  {cat}: {', '.join(available)}")

    # Common action examples
    lines.append("")
    lines.append("KEY EXAMPLES:")
    lines.append('  {{"action": "click", "x": 100, "y": 200}}')
    lines.append('  {{"action": "type_text", "text": "hello"}}')
    lines.append('  {{"action": "press_key", "key": "enter"}}')
    lines.append('  {{"action": "hotkey", "keys": ["ctrl", "c"]}}')
    lines.append('  {{"action": "open_app", "app": "notepad"}}')
    lines.append('  {{"action": "open_url", "url": "https://..."}}')
    lines.append('  {{"action": "file_op", "op": "list", "path": "C:/"}}')
    lines.append('  {{"action": "file_op", "op": "read", "path": "file.txt"}}')
    lines.append('  {{"action": "file_op", "op": "write", "path": "file.txt", "content": "data"}}')
    lines.append('  {{"action": "run_shell", "cmd": "dir"}}')
    lines.append('  {{"action": "run_python", "code": "print(1+1)"}}')
    lines.append('  {{"action": "find_files", "pattern": "*.txt", "path": "C:/Users"}}')
    lines.append('  {{"action": "download_file", "url": "...", "dest": "..."}}')
    lines.append('  {{"action": "scrape_webpage", "url": "..."}}')
    lines.append('  {{"action": "http_request", "url": "...", "method": "GET"}}')
    lines.append('  {{"action": "wait_for_text", "text": "Ready", "timeout": 10}}')
    lines.append('  {{"action": "screenshot_ocr"}}')
    lines.append('  {{"action": "scroll", "direction": "down", "clicks": 3}}')
    lines.append('  {{"action": "done", "message": "Task completed"}}')

    return "\n".join(lines)


def ask_brain(
    goal: str, screen_context: str, history: list,
    task_info: dict, memory: Optional[AgentMemory] = None,
    sub_tasks: Optional[list] = None,
    current_sub_task: int = 0
) -> dict:
    """Send comprehensive context to LLM, get structured action."""
    print(c("  [Brain] Planning next move...", Colors.BLUE))

    recent = history[-8:]

    # Build memory context
    memory_context = ""
    if memory:
        strategies = memory.get_relevant_strategies(goal)
        if strategies:
            memory_context += (
                "\nRELEVANT PAST STRATEGIES:\n"
                + json.dumps(strategies, indent=2) + "\n"
            )
        failures = memory.get_failure_lessons(3)
        if failures:
            memory_context += (
                "\nPAST FAILURES TO AVOID:\n"
                + json.dumps(failures, indent=2) + "\n"
            )
        env_facts = memory.get_environment_summary()
        if env_facts != "No environment facts stored yet.":
            memory_context += (
                "\nKNOWN ENVIRONMENT FACTS:\n" + env_facts + "\n"
            )

    # Sub-task context
    subtask_context = ""
    if sub_tasks and len(sub_tasks) > 1:
        subtask_context = (
            f"\nTASK PLAN ({current_sub_task + 1}/{len(sub_tasks)}):\n"
        )
        for i, st in enumerate(sub_tasks):
            marker = "→" if i == current_sub_task else " "
            status = (
                "✓" if i < current_sub_task
                else "…" if i == current_sub_task
                else " "
            )
            subtask_context += (
                f"  {status} {marker} Step {i+1}: "
                f"{st.get('sub_goal', '?')}\n"
            )

    # Build capabilities string
    caps_summary = ", ".join(
        k for k, v in CAPABILITIES.items() if v
    )

    system_prompt = _build_system_prompt(task_info, caps_summary)

    prompt = (
        f"GOAL: {goal}\n"
        f"{subtask_context}"
        f"{memory_context}\n"
        f"RECENT HISTORY (last {len(recent)} steps):\n"
        f"{json.dumps(recent, indent=2, default=str)}\n\n"
        f"CURRENT SCREEN STATE:\n{screen_context}\n\n"
        "Output ONLY the JSON object for your next action:"
    )

    try:
        raw = _call_llm(prompt, system=system_prompt, timeout=60)

        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if not match:
            raise ValueError(
                f"No JSON found in response:\n{raw[:300]}"
            )

        text = match.group(0)
        # Fix common JSON issues
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)

        result = json.loads(text)

        # Ensure action_command is a dict
        ac = result.get("action_command", {})
        if isinstance(ac, list):
            result["action_command"] = ac[0] if ac else {
                "action": "wait", "seconds": 2
            }

        return result

    except (json.JSONDecodeError, ValueError) as e:
        print(c(f"  [Brain ⚠] Parse error: {e}", Colors.YELLOW))
        log_event({"event": "brain_parse_error", "error": str(e)})
        return {
            "thought": "Parse error — will re-observe screen.",
            "action_command": {"action": "screenshot_ocr"},
            "confidence": 0.3
        }
    except Exception as e:
        print(c(f"  [Brain ⚠] Error: {e}", Colors.RED))
        log_event({"event": "brain_error", "error": str(e)})
        return {
            "thought": "Inference error — pausing to recover.",
            "action_command": {"action": "wait", "seconds": 3},
            "confidence": 0.1
        }


# ─────────────────────────────────────────────────────
# ERROR RECOVERY ENGINE
# ─────────────────────────────────────────────────────
class ErrorRecovery:
    """
    Intelligent error recovery with exponential backoff,
    strategy switching, and fallback chains.
    """

    def __init__(self):
        self.consecutive_errors = 0
        self.error_history = []
        self.strategies_tried = set()

    def handle_error(
        self, error: str, action: dict, history: list
    ) -> Optional[dict]:
        """
        Analyze an error and suggest a recovery action.
        Returns a recovery action dict or None.
        """
        self.consecutive_errors += 1
        self.error_history.append({
            "error": error,
            "action": action,
            "step": len(history)
        })

        # Too many consecutive errors — bail
        if self.consecutive_errors > 5:
            return {
                "action_command": {
                    "action": "fail",
                    "reason": (
                        f"Too many consecutive errors ({self.consecutive_errors}). "
                        f"Last: {error[:100]}"
                    )
                },
                "thought": "Too many errors, giving up."
            }

        action_name = action.get("action", "")

        # Specific recovery strategies
        if "not found" in error.lower():
            if action_name in ("click", "find_and_click_text"):
                return {
                    "action_command": {"action": "screenshot_ocr"},
                    "thought": (
                        "Element not found — taking OCR snapshot "
                        "to find alternative."
                    )
                }

        if "permission" in error.lower():
            return {
                "action_command": {
                    "action": "run_shell",
                    "cmd": (
                        f'powershell Start-Process cmd '
                        f'-Verb RunAs -ArgumentList "/c echo test"'
                    )
                },
                "thought": "Permission error — trying elevated execution."
            }

        if "timeout" in error.lower():
            wait_time = min(2 ** self.consecutive_errors, 10)
            return {
                "action_command": {
                    "action": "wait",
                    "seconds": wait_time
                },
                "thought": (
                    f"Timeout — waiting {wait_time}s "
                    f"before retry."
                )
            }

        if "not installed" in error.lower():
            # Try to identify and install missing package
            match = re.search(
                r"'(\w+)'.*not installed", error
            )
            if match:
                pkg = match.group(1)
                return {
                    "action_command": {
                        "action": "install_package",
                        "package": pkg
                    },
                    "thought": f"Missing package — installing {pkg}."
                }

        # General recovery: observe the screen
        return {
            "action_command": {"action": "screenshot_ocr"},
            "thought": (
                f"Error occurred: {error[:80]}. "
                f"Re-observing screen for alternative approach."
            )
        }

    def record_success(self):
        self.consecutive_errors = 0


# ─────────────────────────────────────────────────────
# SELF-REFLECTION ENGINE
# ─────────────────────────────────────────────────────
class ReflectionEngine:
    """Analyzes performance and generates improvement suggestions."""

    def __init__(self, memory: AgentMemory):
        self.memory = memory

    def reflect_on_run(
        self, goal: str, history: list, success: bool,
        duration: float = 0
    ) -> dict:
        banner("SELF-REFLECTION PHASE", char="·", color=Colors.MAGENTA)

        reflection_prompt = f"""You are reviewing an autonomous OS agent's performance.

TASK GOAL: {goal}
OUTCOME: {"SUCCESS" if success else "FAILURE/INCOMPLETE"}
TOTAL STEPS: {len(history)}
DURATION: {duration:.1f}s

EXECUTION HISTORY:
{json.dumps(history[-15:], indent=2, default=str)}

PAST STATS:
{self.memory.get_summary()}

═══ RESPOND WITH THIS EXACT JSON ═══
{{
  "performance_score": 1-10,
  "bottlenecks": ["what slowed things down"],
  "failures": ["what failed and why"],
  "wasted_steps": ["unnecessary steps"],
  "missing_capabilities": ["tools the agent needed"],
  "strategy_learned": "reusable strategy for this task type",
  "code_improvements": [
    {{
      "target": "function/section to improve",
      "problem": "what's wrong",
      "suggestion": "specific change",
      "priority": "high/medium/low"
    }}
  ],
  "new_tool_ideas": [
    {{
      "name": "tool_name",
      "description": "what it does",
      "implementation_sketch": "rough code"
    }}
  ],
  "overall_assessment": "1-2 sentence summary"
}}"""

        try:
            raw = _call_llm(
                reflection_prompt,
                system=(
                    "You are a critical code reviewer. "
                    "Be honest and specific. Output ONLY valid JSON."
                ),
                timeout=90
            )

            clean = re.sub(r"```(?:json)?|```", "", raw).strip()
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if match:
                reflection = json.loads(match.group(0))
            else:
                reflection = {
                    "error": "Could not parse",
                    "raw": raw[:300]
                }

        except Exception as e:
            reflection = {"error": str(e), "performance_score": 0}

        log_event({
            "event": "reflection",
            "goal": goal,
            "success": success,
            "reflection": reflection
        }, logfile=REFLECTION_LOG)

        self._extract_lessons(goal, history, reflection, success)
        self._print_reflection(reflection)

        return reflection

    def _extract_lessons(
        self, goal, history, reflection, success
    ):
        if success and "strategy_learned" in reflection:
            self.memory.add_strategy(goal, {
                "description": reflection["strategy_learned"],
                "steps_used": len(history),
                "score": reflection.get("performance_score", 5)
            })

        for failure in reflection.get("failures", []):
            self.memory.add_failure(
                context=goal,
                error=failure,
                lesson=reflection.get(
                    "strategy_learned", "No lesson"
                )
            )

        for tool_idea in reflection.get("new_tool_ideas", []):
            self.memory.add_tool_note(
                tool_idea.get("name", "unknown"),
                tool_idea.get("description", "")
            )

        task_type = TaskClassifier.classify(goal).get(
            "primary_type", "general"
        )
        self.memory.record_task_completion(
            success, len(history), task_type=task_type
        )

    def _print_reflection(self, reflection: dict):
        score = reflection.get("performance_score", "?")
        print(c(f"\n  Performance Score: {score}/10", Colors.CYAN))

        if reflection.get("bottlenecks"):
            print(c(
                f"  Bottlenecks: "
                f"{', '.join(reflection['bottlenecks'][:3])}",
                Colors.YELLOW
            ))

        improvements = reflection.get("code_improvements", [])
        if improvements:
            print(c(
                f"  Improvements Suggested: {len(improvements)}",
                Colors.CYAN
            ))
            for imp in improvements[:3]:
                priority = imp.get("priority", "?")
                target = imp.get("target", "?")
                print(c(
                    f"    [{priority.upper()}] {target}: "
                    f"{imp.get('problem', '')[:50]}",
                    Colors.DIM
                ))

        assessment = reflection.get("overall_assessment", "N/A")
        print(c(f"  Assessment: {assessment}", Colors.CYAN))


# ─────────────────────────────────────────────────────
# SELF-MODIFICATION ENGINE
# ─────────────────────────────────────────────────────
class SelfModificationEngine:
    """Generates, validates, and applies code patches."""

    def __init__(self, memory: AgentMemory):
        self.memory = memory
        Path(PATCH_HISTORY).mkdir(exist_ok=True)
        Path(BACKUP_DIR).mkdir(exist_ok=True)

    def backup_current_source(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = Path(BACKUP_DIR) / f"agent_v{timestamp}.py"
        shutil.copy2(AGENT_SOURCE, backup)
        print(c(f"  [Backup] {backup}", Colors.DIM))
        return str(backup)

    def generate_patch(self, reflection: dict) -> Optional[dict]:
        improvements = reflection.get("code_improvements", [])
        new_tools = reflection.get("new_tool_ideas", [])

        if not improvements and not new_tools:
            print("  [Self-Mod] No improvements to apply.")
            return None

        current_source = Path(AGENT_SOURCE).read_text(
            encoding="utf-8"
        )

        patch_prompt = f"""Modify this Python agent's source code to improve it.

KEY SECTIONS OF CURRENT CODE:
{self._get_key_sections(current_source)}

IMPROVEMENTS TO IMPLEMENT:
{json.dumps(improvements, indent=2)}

NEW TOOLS TO ADD:
{json.dumps(new_tools, indent=2)}

RULES:
1. Output ONLY valid JSON
2. Each patch has find/replace text
3. Must be valid Python
4. Don't break existing functionality
5. Keep changes minimal

OUTPUT:
{{
  "patches": [
    {{
      "description": "What this patch does",
      "type": "add_function | modify_function | add_tool | fix_bug",
      "find": "exact text to find (or empty for append)",
      "replace": "replacement text",
      "location": "after:function | before:function | end_of_file"
    }}
  ],
  "risk_level": "low | medium | high",
  "test_suggestion": "How to verify"
}}"""

        try:
            raw = _call_llm(
                patch_prompt,
                system=(
                    "You are an expert Python developer. "
                    "Generate precise, safe patches. "
                    "Output ONLY valid JSON."
                ),
                timeout=120
            )

            clean = re.sub(r"```(?:json)?|```", "", raw).strip()
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if match:
                return json.loads(match.group(0))

        except Exception as e:
            print(c(
                f"  [Self-Mod ⚠] Patch generation failed: {e}",
                Colors.RED
            ))

        return None

    def validate_patch(self, patch: dict) -> bool:
        banner("PATCH VALIDATION", char="·", color=Colors.YELLOW)

        risk = patch.get("risk_level", "high")
        print(c(f"  Risk Level: {risk}", Colors.YELLOW))

        if risk == "high":
            print(c(
                "  [⚠] High-risk patch — manual approval required.",
                Colors.RED
            ))
            if input("  Apply? (y/n): ").strip().lower() != "y":
                return False

        source = Path(AGENT_SOURCE).read_text(encoding="utf-8")
        modified = source

        for p in patch.get("patches", []):
            find_text = p.get("find", "")
            replace_text = p.get("replace", "")

            if find_text and find_text in modified:
                modified = modified.replace(
                    find_text, replace_text, 1
                )
            elif (not find_text
                  and p.get("location") == "end_of_file"):
                modified += "\n\n" + replace_text
            else:
                print(c(
                    f"  [⚠] Target not found: "
                    f"{p.get('description', '?')[:50]}",
                    Colors.YELLOW
                ))
                continue

        try:
            ast.parse(modified)
            print(c("  [✓] Syntax OK.", Colors.GREEN))
        except SyntaxError as e:
            print(c(f"  [✗] Syntax error: {e}", Colors.RED))
            return False

        critical = [
            "run_agent", "execute", "ask_brain",
            "main", "Perception", "ActionExecutor"
        ]
        for func in critical:
            if func not in modified:
                print(c(
                    f"  [✗] Missing critical: '{func}'",
                    Colors.RED
                ))
                return False

        print(c("  [✓] Critical elements preserved.", Colors.GREEN))
        return True

    def apply_patch(self, patch: dict) -> bool:
        banner(
            "APPLYING SELF-MODIFICATION",
            char="═", color=Colors.MAGENTA
        )

        backup_path = self.backup_current_source()
        source = Path(AGENT_SOURCE).read_text(encoding="utf-8")
        modified = source
        applied = 0

        for p in patch.get("patches", []):
            desc = p.get("description", "unnamed")
            find_text = p.get("find", "")
            replace_text = p.get("replace", "")

            if find_text and find_text in modified:
                modified = modified.replace(
                    find_text, replace_text, 1
                )
                print(c(f"  [✓] {desc[:60]}", Colors.GREEN))
                applied += 1
            elif (not find_text
                  and p.get("location") == "end_of_file"):
                modified += "\n\n" + replace_text
                print(c(f"  [✓] Appended: {desc[:60]}", Colors.GREEN))
                applied += 1
            else:
                print(c(
                    f"  [⚠] Skipped: {desc[:60]}",
                    Colors.YELLOW
                ))

        if applied == 0:
            print("  No patches applied.")
            return False

        # Show diff
        diff = list(difflib.unified_diff(
            source.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile="before.py", tofile="after.py", n=3
        ))

        if diff:
            print(c("\n  ─── DIFF PREVIEW ───", Colors.DIM))
            for line in diff[:40]:
                if line.startswith("+"):
                    print(c(f"  {line.rstrip()}", Colors.GREEN))
                elif line.startswith("-"):
                    print(c(f"  {line.rstrip()}", Colors.RED))
                else:
                    print(f"  {line.rstrip()}")
            if len(diff) > 40:
                print(c(
                    f"  ... ({len(diff) - 40} more lines)",
                    Colors.DIM
                ))

        print(f"\n  Patches: {applied} | Backup: {backup_path}")
        if input("  Apply changes? (y/n): ").strip().lower() != "y":
            print("  [Cancelled]")
            return False

        Path(AGENT_SOURCE).write_text(modified, encoding="utf-8")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        patch_file = (
            Path(PATCH_HISTORY) / f"patch_{timestamp}.json"
        )
        patch_file.write_text(
            json.dumps(patch, indent=2), encoding="utf-8"
        )

        self.memory.data["code_improvements"].append({
            "timestamp": datetime.now().isoformat(),
            "patches": applied,
            "backup": backup_path,
            "descriptions": [
                p.get("description", "")
                for p in patch.get("patches", [])
            ]
        })
        self.memory.save()

        log_event({
            "event": "self_modification",
            "patches": applied,
            "backup": backup_path,
        }, logfile=IMPROVEMENT_LOG)

        banner(
            f"✓ {applied} patches applied!",
            char="═", color=Colors.GREEN
        )
        return True

    def rollback(self) -> bool:
        backups = sorted(Path(BACKUP_DIR).glob("agent_v*.py"))
        if not backups:
            print("No backups found.")
            return False

        latest = backups[-1]
        print(f"Rolling back to: {latest.name}")
        if input("Confirm? (y/n): ").strip().lower() == "y":
            shutil.copy2(str(latest), AGENT_SOURCE)
            print(c(f"[✓] Rolled back to {latest.name}", Colors.GREEN))
            return True
        return False

    def _get_key_sections(
        self, source: str, max_len: int = 5000
    ) -> str:
        sections = []
        important = [
            "SYSTEM_PROMPT", "def execute", "def ask_brain",
            "def run_agent", "class Perception",
            "class ActionExecutor", "class TaskClassifier"
        ]
        lines = source.split("\n")
        for keyword in important:
            for i, line in enumerate(lines):
                if keyword in line:
                    start = max(0, i - 2)
                    end = min(len(lines), i + 25)
                    sections.append(
                        f"--- {keyword} (line {i}) ---\n"
                        + "\n".join(lines[start:end])
                    )
                    break

        result = "\n\n".join(sections)
        return result[:max_len]


# ─────────────────────────────────────────────────────
# SELF-IMPROVEMENT ORCHESTRATOR
# ─────────────────────────────────────────────────────
class SelfImprovementOrchestrator:
    """Coordinates reflect → patch → validate → apply."""

    def __init__(self):
        self.memory = AgentMemory()
        self.reflector = ReflectionEngine(self.memory)
        self.modifier = SelfModificationEngine(self.memory)

    def post_task_improvement(
        self, goal: str, history: list,
        success: bool, duration: float = 0
    ):
        reflection = self.reflector.reflect_on_run(
            goal, history, success, duration
        )

        score = reflection.get("performance_score", 10)
        improvements = reflection.get("code_improvements", [])

        should_modify = (
            score < 7
            or len(improvements) > 0
            or len(reflection.get("new_tool_ideas", [])) > 0
        )

        if not should_modify:
            print(c(
                "\n  [Self-Improve] Performance OK. "
                "No modifications needed.",
                Colors.GREEN
            ))
            return

        print(c(
            f"\n  [Self-Improve] Score {score}/10, "
            f"{len(improvements)} suggestions. "
            f"Generating patches...",
            Colors.MAGENTA
        ))

        patch = self.modifier.generate_patch(reflection)
        if not patch:
            return

        if not self.modifier.validate_patch(patch):
            print("  [Self-Improve] Validation failed. Skipping.")
            return

        self.modifier.apply_patch(patch)

    def dedicated_improvement_session(self):
        banner(
            "DEDICATED SELF-IMPROVEMENT SESSION",
            char="═", color=Colors.MAGENTA
        )
        print(c(
            f"  Stats: {self.memory.get_summary()}",
            Colors.CYAN
        ))

        reflections = []
        if Path(REFLECTION_LOG).exists():
            with open(REFLECTION_LOG, "r") as f:
                for line in f:
                    try:
                        reflections.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        if not reflections:
            print(
                "  No past reflections. "
                "Run tasks with --improve first."
            )
            return

        meta_prompt = f"""Strategic review of an autonomous OS agent.

STATS: {self.memory.get_summary()}

LAST 10 REFLECTIONS:
{json.dumps(reflections[-10:], indent=2, default=str)}

FAILURES:
{json.dumps(self.memory.data['failure_patterns'][-10:], indent=2)}

IMPROVEMENTS APPLIED:
{json.dumps(self.memory.data['code_improvements'][-10:], indent=2)}

Output ONLY JSON:
{{
  "analysis": "Overall assessment",
  "top_recurring_issues": ["issue1", "issue2"],
  "code_improvements": [
    {{
      "target": "function/section",
      "problem": "what's wrong",
      "suggestion": "specific change",
      "priority": "high/medium/low",
      "expected_impact": "how this helps"
    }}
  ],
  "new_tool_ideas": [
    {{
      "name": "tool_name",
      "description": "what it does",
      "implementation_sketch": "rough code"
    }}
  ],
  "architectural_suggestions": ["suggestion1"]
}}"""

        try:
            raw = _call_llm(
                meta_prompt,
                system=(
                    "You are a senior AI architect. "
                    "Be specific and prioritize high-impact changes. "
                    "Output ONLY valid JSON."
                ),
                timeout=120
            )

            clean = re.sub(r"```(?:json)?|```", "", raw).strip()
            match = re.search(r"\{.*\}", clean, re.DOTALL)

            if not match:
                print("  [⚠] Could not parse review.")
                return

            review = json.loads(match.group(0))

            print(c(
                f"\n  Analysis: {review.get('analysis', 'N/A')}",
                Colors.CYAN
            ))

            for issue in review.get("top_recurring_issues", []):
                print(c(f"    • {issue}", Colors.YELLOW))

            improvements = review.get("code_improvements", [])
            if improvements:
                print(c(
                    f"\n  Improvements ({len(improvements)}):",
                    Colors.CYAN
                ))
                for imp in improvements:
                    print(c(
                        f"    [{imp.get('priority','?').upper()}] "
                        f"{imp.get('target','?')}: "
                        f"{imp.get('problem','?')[:50]}",
                        Colors.DIM
                    ))

            if improvements or review.get("new_tool_ideas"):
                apply = input(
                    "\n  Generate and apply patches? (y/n): "
                ).strip().lower()
                if apply == "y":
                    patch = self.modifier.generate_patch(review)
                    if patch and self.modifier.validate_patch(patch):
                        self.modifier.apply_patch(patch)

        except Exception as e:
            print(c(f"  [⚠] Review failed: {e}", Colors.RED))


# ─────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────
def _human_size(nbytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(nbytes) < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} PB"


def _fuzzy_match(a: str, b: str, threshold: float = 0.5) -> bool:
    a_words = set(a.lower().split())
    b_words = set(b.lower().split())
    if not a_words or not b_words:
        return False
    overlap = len(a_words & b_words)
    return overlap / max(len(a_words), len(b_words)) >= threshold


def check_prerequisites() -> dict:
    """Check what's available and what's missing."""
    checks = {
        "ollama": False,
        "ollama_model": False,
    }

    # Check Ollama
    try:
        resp = requests.get(
            "http://localhost:11434/api/tags", timeout=5
        )
        checks["ollama"] = resp.status_code == 200
        if checks["ollama"]:
            models = [
                m["name"]
                for m in resp.json().get("models", [])
            ]
            checks["ollama_model"] = any(
                MODEL_NAME.split(":")[0] in m
                for m in models
            )
            checks["available_models"] = models
    except Exception:
        pass

    checks.update(CAPABILITIES)
    return checks


def print_capability_report():
    """Show what the agent can and can't do."""
    checks = check_prerequisites()

    print(c("\n  ═══ CAPABILITY REPORT ═══", Colors.CYAN))

    status_icon = lambda v: c("✓", Colors.GREEN) if v else c("✗", Colors.RED)

    print(f"  {status_icon(checks.get('ollama'))} "
          f"Ollama Server")
    print(f"  {status_icon(checks.get('ollama_model'))} "
          f"Model: {MODEL_NAME}")
    print(f"  {status_icon(checks.get('pyautogui'))} "
          f"PyAutoGUI (mouse/keyboard)")
    print(f"  {status_icon(checks.get('uiautomation'))} "
          f"UI Automation (element tree)")
    print(f"  {status_icon(checks.get('ocr'))} "
          f"Tesseract OCR (screen reading)")
    print(f"  {status_icon(checks.get('pil'))} "
          f"PIL/Pillow (image processing)")
    print(f"  {status_icon(checks.get('clipboard'))} "
          f"Pyperclip (clipboard)")
    print(f"  {status_icon(checks.get('psutil'))} "
          f"PSUtil (process management)")
    print(f"  {status_icon(checks.get('beautifulsoup'))} "
          f"BeautifulSoup (web scraping)")
    print(f"  {status_icon(checks.get('win32'))} "
          f"Win32 API (advanced Windows)")
    print(f"  {status_icon(checks.get('keyboard'))} "
          f"Keyboard module")
    print(f"  {status_icon(checks.get('mouse'))} "
          f"Mouse module")

    if not checks.get("ollama"):
        print(c(
            "\n  ⚠ Ollama not running! Start with: ollama serve",
            Colors.RED
        ))
    elif not checks.get("ollama_model"):
        available = checks.get("available_models", [])
        print(c(
            f"\n  ⚠ Model '{MODEL_NAME}' not found. "
            f"Available: {available}",
            Colors.YELLOW
        ))

    print()


def save_task_state(state: dict):
    """Save current task state for resumption."""
    with open(TASK_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)


def load_task_state() -> Optional[dict]:
    """Load saved task state."""
    if Path(TASK_STATE_FILE).exists():
        try:
            with open(TASK_STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────────────
# MAIN AGENT LOOP
# ─────────────────────────────────────────────────────
def run_agent(
    goal: str,
    max_steps: int = 20,
    safe_mode: bool = False,
    improve: bool = False,
    verbose: bool = False,
    plan_only: bool = False,
):
    """
    The main agent loop that can handle ANY task.

    1. Classify task type
    2. Decompose into sub-tasks
    3. Execute with error recovery
    4. Learn from experience
    """
    start_time = time.time()
    memory = AgentMemory()

    # ── Classify Task ──
    task_info = TaskClassifier.classify(goal)

    banner(
        f"UNIVERSAL OS AGENT v4.0\n"
        f"Goal: {goal}\n"
        f"Type: {task_info['primary_type']} | "
        f"Complexity: {task_info['complexity']}\n"
        f"Steps: {max_steps} | Safe: {safe_mode} | "
        f"Improve: {improve}\n"
        f"Memory: {memory.get_summary()}",
        char="═", color=Colors.CYAN
    )

    # ── Check for destructive operations ──
    if task_info["is_destructive"] and not safe_mode:
        print(c(
            "\n  ⚠ DESTRUCTIVE TASK DETECTED! "
            "Consider using --safe mode.",
            Colors.RED
        ))
        if input("  Continue anyway? (y/n): ").strip().lower() != "y":
            return False, []

    # ── Decompose Task ──
    sub_tasks = TaskDecomposer.decompose(goal, task_info, memory)

    if len(sub_tasks) > 1:
        print(c(f"\n  Task decomposed into {len(sub_tasks)} steps:",
                Colors.CYAN))
        for i, st in enumerate(sub_tasks):
            print(c(
                f"    {i+1}. {st.get('sub_goal', '?')}", Colors.DIM
            ))
        print()

    if plan_only:
        banner("PLAN COMPLETE (--plan-only mode)", color=Colors.GREEN)
        return True, []

    log_event({
        "event": "start",
        "goal": goal,
        "task_info": task_info,
        "sub_tasks": sub_tasks,
        "max_steps": max_steps,
    })

    # ── Initialize ──
    executor = ActionExecutor(safe_mode=safe_mode)
    error_recovery = ErrorRecovery()
    history: List[dict] = []
    success = False
    current_sub_task = 0

    # ── Main Loop ──
    for step in range(1, max_steps + 1):
        sub_goal = (
            sub_tasks[current_sub_task].get("sub_goal", goal)
            if current_sub_task < len(sub_tasks)
            else goal
        )

        step_header(
            step, max_steps,
            phase=f"Sub-task {current_sub_task + 1}"
            if len(sub_tasks) > 1 else ""
        )

        # ── Observe ──
        include_ocr = (
            task_info.get("needs_gui", False)
            or step % 3 == 0  # Periodic OCR
        )

        screen = Perception.get_full_context(
            include_ocr=include_ocr,
            include_processes=(step == 1 or step % 10 == 0),
            include_clipboard=(step == 1),
        )

        if verbose:
            print(c(f"\n  [Screen Context]\n{screen[:500]}",
                    Colors.DIM))

        # ── Think ──
        response = ask_brain(
            goal=goal,
            screen_context=screen,
            history=history,
            task_info=task_info,
            memory=memory,
            sub_tasks=sub_tasks if len(sub_tasks) > 1 else None,
            current_sub_task=current_sub_task,
        )

        thought = response.get("thought", "—")
        action = response.get("action_command", {})
        confidence = response.get("confidence", 0.5)

        print_thought(thought)

        if verbose:
            print(c(
                f"  [Confidence: {confidence}]",
                Colors.DIM
            ))

        # Handle list actions
        if isinstance(action, list):
            print(c(
                "  [⚠] List returned — using first item.",
                Colors.YELLOW
            ))
            action = action[0] if action else {
                "action": "wait", "seconds": 2
            }

        # ── Act ──
        done, obs = executor.execute(action)

        # Track tool usage
        memory.record_tool_usage(action.get("action", "unknown"))

        # ── Error Recovery ──
        if "error" in obs.lower() or "not found" in obs.lower():
            recovery = error_recovery.handle_error(
                obs, action, history
            )
            if recovery:
                rec_action = recovery.get("action_command", {})
                rec_thought = recovery.get("thought", "")
                if rec_action.get("action") == "fail":
                    done = True
                    obs = rec_action.get("reason", "Failed")
                    success = False
                else:
                    print(c(
                        f"  [Recovery] {rec_thought}",
                        Colors.YELLOW
                    ))
                    # Execute recovery action
                    _, rec_obs = executor.execute(rec_action)
                    obs += f" → Recovery: {rec_obs}"
        else:
            error_recovery.record_success()

        # ── Record ──
        step_record = {
            "step": step,
            "sub_task": current_sub_task,
            "thought": thought,
            "action": action,
            "observation": obs[:500],
            "confidence": confidence,
        }
        history.append(step_record)
        log_event({"event": "step", **step_record})

        # ── Save state for resume ──
        save_task_state({
            "goal": goal,
            "step": step,
            "history": history,
            "current_sub_task": current_sub_task,
            "success": False,
        })

        # ── Check completion ──
        if done:
            if "FAILED" in obs:
                success = False
            else:
                success = True
            break

        # ── Advance sub-task ──
        if (response.get("sub_goal", "")
                and "complete" in response.get("sub_goal", "").lower()):
            if current_sub_task < len(sub_tasks) - 1:
                current_sub_task += 1
                print(c(
                    f"\n  ▶ Advancing to sub-task "
                    f"{current_sub_task + 1}: "
                    f"{sub_tasks[current_sub_task].get('sub_goal', '')}",
                    Colors.CYAN
                ))

        time.sleep(0.8)

    else:
        banner(
            f"Max steps ({max_steps}) reached. "
            f"Goal may be incomplete.",
            char="─", color=Colors.YELLOW
        )
        log_event({"event": "max_steps_reached", "goal": goal})

    # ── Duration ──
    duration = time.time() - start_time
    print(c(
        f"\n  Duration: {duration:.1f}s | "
        f"Steps: {len(history)} | "
        f"Success: {success}",
        Colors.CYAN
    ))

    # ── Clean up task state ──
    if success:
        try:
            Path(TASK_STATE_FILE).unlink(missing_ok=True)
        except Exception:
            pass

    # ── Post-task self-improvement ──
    if improve:
        orchestrator = SelfImprovementOrchestrator()
        orchestrator.post_task_improvement(
            goal, history, success, duration
        )

    print(c(
        f"\n  [Log] Session saved → {AGENT_LOG}\n",
        Colors.DIM
    ))
    return success, history


# ─────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Universal Self-Improving Autonomous OS Agent v4.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        ═══ EXAMPLES ═══

        Basic tasks:
          python agent.py "open notepad and type hello world"
          python agent.py "take a screenshot and save it to desktop"
          python agent.py "find all PDF files in Documents"

        Web tasks:
          python agent.py "open chrome and search for Python tutorials"
          python agent.py "download the file from https://example.com/data.csv"
          python agent.py "scrape the headlines from news.ycombinator.com"

        File management:
          python agent.py "organize files on Desktop by extension"
          python agent.py "find and delete all .tmp files in Downloads"
          python agent.py "create a backup of the Projects folder"

        System tasks:
          python agent.py "show me system information"
          python agent.py "list all running processes using more than 100MB RAM"
          python agent.py "check if port 8080 is in use"

        Coding:
          python agent.py "write a Python script that calculates fibonacci numbers"
          python agent.py "create an HTML page with a contact form"

        Complex:
          python agent.py --max-steps 40 "open Excel, create a budget spreadsheet"
          python agent.py --safe "clean up temporary files from the system"

        Self-improvement:
          python agent.py --improve "open notepad and type a poem"
          python agent.py --self-improve
          python agent.py --review-memory
          python agent.py --rollback
        """)
    )

    parser.add_argument(
        "goal", nargs="*", help="Goal in plain English"
    )
    parser.add_argument(
        "--max-steps", type=int, default=25, metavar="N",
        help="Max agent steps (default: 25)"
    )
    parser.add_argument(
        "--safe", action="store_true",
        help="Confirm destructive actions"
    )
    parser.add_argument(
        "--model", type=str,
        help="Override Ollama model name"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Extra debug output"
    )
    parser.add_argument(
        "--improve", action="store_true",
        help="Enable post-task self-improvement"
    )
    parser.add_argument(
        "--self-improve", action="store_true",
        help="Dedicated self-improvement session"
    )
    parser.add_argument(
        "--review-memory", action="store_true",
        help="Show learned strategies and stats"
    )
    parser.add_argument(
        "--rollback", action="store_true",
        help="Revert to previous version"
    )
    parser.add_argument(
        "--plan-only", action="store_true",
        help="Show task plan without executing"
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume last interrupted task"
    )
    parser.add_argument(
        "--capabilities", action="store_true",
        help="Show capability report"
    )

    args = parser.parse_args()

    if args.model:
        global MODEL_NAME
        MODEL_NAME = args.model

    # ── Special modes ──
    if args.capabilities:
        print_capability_report()
        return

    if args.rollback:
        memory = AgentMemory()
        modifier = SelfModificationEngine(memory)
        modifier.rollback()
        return

    if args.review_memory:
        memory = AgentMemory()
        banner("AGENT MEMORY REVIEW", char="═", color=Colors.CYAN)
        print(c(f"\n  {memory.get_summary()}\n", Colors.WHITE))

        print(c("  ── Learned Strategies ──", Colors.CYAN))
        for s in memory.data["learned_strategies"][-10:]:
            print(c(
                f"    • {s['pattern'][:50]}: "
                f"{json.dumps(s['strategy'])[:80]}",
                Colors.DIM
            ))

        print(c("\n  ── Failure Patterns ──", Colors.CYAN))
        for f in memory.data["failure_patterns"][-10:]:
            print(c(f"    ✗ {f['error'][:60]}", Colors.RED))
            print(c(f"      Lesson: {f['lesson'][:60]}", Colors.DIM))

        print(c("\n  ── Code Improvements ──", Colors.CYAN))
        for ci in memory.data["code_improvements"][-10:]:
            print(c(
                f"    [{ci['timestamp'][:10]}] "
                f"{ci.get('descriptions', [])}",
                Colors.DIM
            ))

        print(c("\n  ── Environment Facts ──", Colors.CYAN))
        print(c(f"  {memory.get_environment_summary()}", Colors.DIM))

        stats = memory.data["performance_stats"]
        print(c("\n  ── Tool Usage ──", Colors.CYAN))
        sorted_tools = sorted(
            stats.get("tool_usage_counts", {}).items(),
            key=lambda x: x[1], reverse=True
        )
        for tool, count in sorted_tools[:15]:
            print(c(f"    {tool}: {count}", Colors.DIM))

        print(c("\n  ── Task Type Success Rates ──", Colors.CYAN))
        for tt, data in stats.get("task_type_success", {}).items():
            rate = (
                round(data["successes"] / data["attempts"] * 100)
                if data["attempts"] > 0 else 0
            )
            print(c(
                f"    {tt}: {rate}% "
                f"({data['successes']}/{data['attempts']})",
                Colors.DIM
            ))

        return

    if args.self_improve:
        orchestrator = SelfImprovementOrchestrator()
        orchestrator.dedicated_improvement_session()
        return

    if args.resume:
        state = load_task_state()
        if state:
            print(c(
                f"  Resuming task: {state['goal']}",
                Colors.CYAN
            ))
            goal = state["goal"]
            # Continue from where we left off
            run_agent(
                goal,
                max_steps=args.max_steps,
                safe_mode=args.safe,
                improve=args.improve,
                verbose=args.verbose,
            )
        else:
            print("No saved task state found.")
        return

    # ── Normal task mode ──
    if args.goal:
        goal = " ".join(args.goal)
    else:
        print(c("\n" + "═" * 62, Colors.CYAN))
        print(c(
            "  UNIVERSAL AUTONOMOUS OS AGENT v4.0",
            Colors.BOLD + Colors.CYAN
        ))
        print(c(
            "  Can do ANY task: GUI, Web, Files, Code, System, Research",
            Colors.DIM
        ))
        print(c("═" * 62, Colors.CYAN))
        print(c(
            "  Type your goal in plain English. "
            "Be specific for best results.",
            Colors.WHITE
        ))
        print(c(
            "  Use --capabilities to see what's available.",
            Colors.DIM
        ))
        print(c("─" * 62, Colors.DIM))

        goal = input(c("\n  Goal: ", Colors.GREEN)).strip()
        if not goal:
            print("No goal given. Exiting.")
            sys.exit(0)

    # Quick prereq check
    checks = check_prerequisites()
    if not checks.get("ollama"):
        print(c(
            "\n  ⚠ Ollama not running! "
            "Start with: ollama serve",
            Colors.RED
        ))
        sys.exit(1)

    # Auto-adjust max steps for complex tasks
    task_info = TaskClassifier.classify(goal)
    if (task_info["complexity"] == "complex"
            and args.max_steps == 25):
        adjusted_steps = task_info["estimated_steps"]
        if adjusted_steps > args.max_steps:
            print(c(
                f"\n  [Auto] Complex task detected. "
                f"Adjusting max steps: "
                f"{args.max_steps} → {adjusted_steps}",
                Colors.YELLOW
            ))
            args.max_steps = adjusted_steps

    print(c(
        f"\n  [!] Starting in 3 seconds... "
        f"(move mouse to screen corner to abort)",
        Colors.YELLOW
    ))
    time.sleep(3)

    run_agent(
        goal,
        max_steps=args.max_steps,
        safe_mode=args.safe,
        improve=args.improve,
        verbose=args.verbose,
        plan_only=args.plan_only,
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import re
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)
from pathlib import Path


def build_preview_placeholder_html(*, lang: str = "vi", title: str = "EduPlay Preview") -> str:
    is_vi = (lang or "").strip().lower().startswith("vi")
    try:
        from eduplay.core.i18n import I18n
        heading = I18n.t("preview.placeholder_heading", lang)
        sub = I18n.t("preview.placeholder_sub", lang)
    except Exception:
        heading = "Đang tải bản xem trước..." if is_vi else "Loading preview..."
        sub = "Vui lòng chờ trong giây lát." if is_vi else "Please wait a moment."
    safe_title = (title or "EduPlay Preview").replace("<", "").replace(">", "").replace("&", "and")
    return f"""<!doctype html>
<html lang="{('vi' if is_vi else 'en')}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title}</title>
  <style>
    html, body {{
      height: 100%;
      margin: 0;
      font-family: "Times New Roman", Times, serif;
      background: #0b1020;
      color: #e5e7eb;
    }}
    #eduplay-preview-placeholder {{
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 32px;
      box-sizing: border-box;
    }}
    .box {{
      width: min(560px, 100%);
      min-width: 0;
      overflow-wrap: anywhere;
      word-break: break-word;
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.06);
      backdrop-filter: blur(8px);
      padding: 22px 22px 18px;
    }}
    .row {{
      display: flex;
      gap: 14px;
      align-items: center;
    }}
    .spinner {{
      width: 30px;
      height: 30px;
      border-radius: 999px;
      border: 3px solid rgba(255, 255, 255, 0.25);
      border-top-color: rgba(127, 86, 217, 1);
      animation: spin 0.9s linear infinite;
      flex: 0 0 auto;
    }}
    h1 {{
      margin: 0;
      font-size: 19px;
      font-weight: 700;
      line-height: 1.25;
    }}
    p {{
      margin: 10px 0 0;
      font-size: 14px;
      opacity: 0.9;
      line-height: 1.5;
    }}
    @keyframes spin {{
      from {{ transform: rotate(0deg); }}
      to {{ transform: rotate(360deg); }}
    }}
  </style>
</head>
<body>
  <div id="eduplay-preview-placeholder">
    <div class="box">
      <div class="row">
        <div class="spinner" aria-hidden="true"></div>
        <h1>{heading}</h1>
      </div>
      <p>{sub}</p>
    </div>
  </div>
  <script>
    // Tận dụng RAM: preload, fade mượt, reload 1 lần sau 1.4s (đủ cho thread ghi file 11MB)
    (function(){{
      document.documentElement.style.transition='opacity 220ms ease';
      setTimeout(function(){{
        document.documentElement.style.opacity='0';
        setTimeout(function(){{ window.location.reload(); }}, 220);
      }}, 1400);
    }})();
  </script>
</body>
</html>
"""


def inject_quick_preview_autostart(html: str, question_index: int = 0) -> str:
    """Inject quick-preview auto-start bootstrap into generated game HTML.

    Sets ``window.__EDUPLAY_QUICK_PREVIEW_AUTO_START`` and installs the
    quick-preview hooks needed to skip menus and open the specified question.

    *Idempotent*: re-injecting already-bootstrapped HTML is a no-op.

    Args:
        html: The HTML string to inject into.
        question_index: The zero-based question index to open automatically.
            Use ``0`` to open the first question, ``1`` for the second, etc.
    """
    html = str(html or "")
    if not html:
        return html

    marker = 'window["__EDUPLAY_QUICK_PREVIEW_AUTO_START"] = true;'
    if marker in html and "window.__EDUPLAY_QUICK_PREVIEW_BOOTSTRAPPED" in html:
        return html

    early_style = (
        '<style id="eduplay-quick-preview-early-style">'
        '#start-overlay, #intro-screen, #mainMenu, #preloader { display: none !important; }'
        'html, body { -webkit-app-region: no-drag; }'
        '</style>'
    )

    script = """<script>
(function () {
  console.log('[Preview] Bootstrap script running');
  if (window.__EDUPLAY_QUICK_PREVIEW_BOOTSTRAPPED) {
    console.log('[Preview] Already bootstrapped, skipping');
    return;
  }
  window.__EDUPLAY_QUICK_PREVIEW_BOOTSTRAPPED = true;
  window["__EDUPLAY_QUICK_PREVIEW_AUTO_START"] = true;
  console.log('[Preview] Set __EDUPLAY_QUICK_PREVIEW_AUTO_START = true');
  window.__EDUPLAY_QUICK_PREVIEW_QUESTION_INDEX = """ + str(int(question_index)) + """;
  window.__EDUPLAY_QUICK_PREVIEW_SINGLE_QUESTION = true;
  window.__EDUPLAY_QUICK_PREVIEW_MILLIONAIRE_RESOLVED = false;

  function isElementVisible(el) {
    if (!el) { return false; }
    var style = window.getComputedStyle ? window.getComputedStyle(el) : null;
    if (style && (style.display === 'none' || style.visibility === 'hidden')) { return false; }
    var rect = el.getBoundingClientRect ? el.getBoundingClientRect() : null;
    if (rect && (rect.width === 0 || rect.height === 0)) { return false; }
    return true;
  }

  function hasVisibleGameplay() {
    var questionText = document.getElementById('question-text');
    if (questionText && isElementVisible(questionText)) { return true; }
    var candidates = [
      document.getElementById('question'),
      document.getElementById('question-panel'),
      document.getElementById('gameWindow'),
      document.getElementById('app')
    ];
    for (var i = 0; i < candidates.length; i++) {
      if (isElementVisible(candidates[i])) { return true; }
    }
    return false;
  }

  window.__EDUPLAY_QUICK_PREVIEW_MARK_STARTED = function () {
    var overlay = document.getElementById('start-overlay');
    if (overlay) { overlay.style.display = 'none'; }
    var intro = document.getElementById('intro-screen');
    if (intro) { intro.style.display = 'none'; }
    var mainMenu = document.getElementById('mainMenu');
    if (mainMenu) { mainMenu.style.display = 'none'; }
    var preloader = document.getElementById('preloader');
    if (preloader) { preloader.style.display = 'none'; }
  };

  window.__EDUPLAY_QUICK_PREVIEW_HIDE_OVERLAY = function () {
    window.__EDUPLAY_QUICK_PREVIEW_MARK_STARTED();
  };

  window.__EDUPLAY_QUICK_PREVIEW_OPEN_QUESTION = function () {
    var question = document.getElementById('question');
    var questionText = document.getElementById('question-text');
    if (question) { question.style.display = ''; }
    if (questionText) { questionText.style.display = ''; }
    var startOverlay = document.getElementById('start-overlay');
    if (startOverlay) { startOverlay.style.display = 'none'; }
    var introScreen = document.getElementById('intro-screen');
    if (introScreen) { introScreen.style.display = 'none'; }
    var mainMenu = document.getElementById('mainMenu');
    if (mainMenu) { mainMenu.style.display = 'none'; }
    var preloader = document.getElementById('preloader');
    if (preloader) { preloader.style.display = 'none'; }
  };

  window.__EDUPLAY_QUICK_PREVIEW_DIRECT_RENDER_FISH = false;
  window.__EDUPLAY_QUICK_PREVIEW_DIRECT_RENDER_MILLIONAIRE = false;

  var introComplete = false;
  window.__EDUPLAY_QUICK_PREVIEW_ON_START_CLICK = function onStartClick() {
    if (introComplete) { return; }
    introComplete = true;
    try {
      ['start-btn', 'startOverlay', 'start-overlay', 'intro-screen', 'mainMenu', 'preloader'].forEach(function (id) {
        var el = document.getElementById(id);
        if (el && el.style) { el.style.display = 'none'; }
      });
      if (typeof window.__EDUPLAY_QUICK_PREVIEW_MARK_STARTED === 'function') {
        window.__EDUPLAY_QUICK_PREVIEW_MARK_STARTED();
      }
    } catch (e) {}
  };
  var startBtn = document.getElementById('start-btn');
  if (startBtn) {
    try { startBtn.addEventListener('click', window.__EDUPLAY_QUICK_PREVIEW_ON_START_CLICK); } catch (e) {}
    try {
      startBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
    } catch (e) {}
  }

  window.__EDUPLAY_QUICK_PREVIEW_OPEN_FIRST_QUESTION = function openFirstQuestionHook() {
    try {
      var overlay = document.getElementById('start-overlay');
      if (overlay && overlay.style) { overlay.style.display = 'none'; }
      if (typeof showQuestion === 'function') { showQuestion(0); }
      if (typeof window.__EDUPLAY_QUICK_PREVIEW_MARK_STARTED === 'function') {
        window.__EDUPLAY_QUICK_PREVIEW_MARK_STARTED();
      }
    } catch (e) {
      console.warn('[Preview] open first question failed:', e);
    }
  };
  window.__EDUPLAY_QUICK_PREVIEW_FALLBACK_OPEN_FIRST_QUESTION = function () {
    try {
      if (typeof window.__EDUPLAY_QUICK_PREVIEW_OPEN_FIRST_QUESTION === 'function') {
        window.__EDUPLAY_QUICK_PREVIEW_OPEN_FIRST_QUESTION();
        return;
      }
      if (typeof showQuestion === 'function') { showQuestion(0); }
    } catch (e) {
      console.warn('[Preview] fallback open first question failed:', e);
    }
  };

  function bindMillionairePreviewAction(target, flagName, handler) {
    if (!target || target[flagName]) { return; }
    target[flagName] = true;
    try { target.addEventListener('click', handler); } catch (e) {}
    try { target.addEventListener('touchend', handler); } catch (e) {}
  }

  function resetMillionairePreviewState(answerBlocks) {
    try {
      (answerBlocks || []).forEach(function (block) {
        if (!block || !block.classList) { return; }
        block.classList.remove('answerCorrect', 'answerIncorrect', 'answerCheck', 'locked');
        var highlightReset = block.highlightAnswerReset || null;
        if (typeof highlightReset === 'function') { highlightReset.call(block); }
      });
    } catch (e) {}
  }

  function installMillionairePreviewAnswerFallback(question, answerBlocks, answerTexts) {
    try {
      // Neu game that da san sang (co highLightAnswerOrange) thi de game that xu ly, khong dung fallback
      if (typeof highLightAnswerOrange === 'function' && typeof highLightAnswerGreen === 'function') {
        return;
      }
      resetMillionairePreviewState(answerBlocks);
      (answerBlocks || []).forEach(function (block) {
        bindMillionairePreviewAction(block, '__EDUPLAY_PREVIEW_ANSWER_BOUND', function (event) {
          try { event.preventDefault(); } catch (e) {}
          try { resetMillionairePreviewState(answerBlocks); } catch (e) {}
          try { block.classList.add('answerCheck'); block.classList.remove('answer'); } catch (e) {}
          // Giu vang y nhu goc WWBM 4s roi moi xoa (khop highLightAnswerGreen 4000)
          window.setTimeout(function () {
            try { block.classList.remove('answerCheck'); block.classList.add('answer'); } catch (e) {}
          }, 4000);
        });
      });
    } catch (e) {
      console.warn('[Preview] millionaire answer fallback failed:', e);
    }
  }

  function bindMillionairePreviewLifelines(question, answerBlocks, answerTexts) {
    try {
      var previewTextNodes = document.querySelectorAll('.answerText, .answerText *, .llText, .llText *');
      if (previewTextNodes && previewTextNodes.length) {
        for (var i = 0; i < previewTextNodes.length; i++) {
          previewTextNodes[i].setAttribute('data-preview-selectable', '1');
        }
      }
      var ans1 = document.getElementById('ans1');
      if (ans1 && answerTexts.indexOf(ans1) < 0) { answerTexts.push(ans1); }
      ['ll5050', 'llPhone', 'llAudience'].forEach(function (id) {
        bindMillionairePreviewAction(document.getElementById(id), '__EDUPLAY_PREVIEW_LIFELINE_BOUND_' + id, function (event) {
          try { event.preventDefault(); } catch (e) {}
        });
      });
      bindMillionairePreviewAction(document.getElementById('ll5050'), '__EDUPLAY_PREVIEW_LIFELINE_5050_BOUND', function (event) {
        try { event.preventDefault(); } catch (e) {}
      });
    } catch (e) {
      console.warn('[Preview] millionaire lifeline binding failed:', e);
    }
  }

  var _installMillionairePreviewControls = function () {
    try {
      var question = document.getElementById('question');
      var answerBlocks = [];
      var answerTexts = [];
      ['ans1B', 'ans2B', 'ans3B', 'ans4B', 'ans1', 'ans2', 'ans3', 'ans4'].forEach(function (id) {
        var el = document.getElementById(id);
        if (!el) { return; }
        if (id.charAt(id.length - 1) === 'B') { answerBlocks.push(el); }
        else { answerTexts.push(el); }
      });
      if (!question || !answerBlocks.length) { return false; }
      installMillionairePreviewAnswerFallback(question, answerBlocks, answerTexts);
      bindMillionairePreviewLifelines(question, answerBlocks, answerTexts);
      return true;
    } catch (e) { return false; }
  };

  var _dispatchQuickPreviewLoad = function () {
    try {
      var loadEvent = document.createEvent('Event');
      loadEvent.initEvent('load', false, false);
      window.dispatchEvent(loadEvent);
    } catch (e) {}
    try {
      var playButton = document.getElementById('playGameBtn');
      if (playButton) {
        playButton.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
      }
    } catch (e) {}
  };

  var lateBootstrap = function () {
    try { _installMillionairePreviewControls(); } catch (e) {}
    try {
      if (typeof window.__EDUPLAY_QUICK_PREVIEW_MARK_STARTED === 'function' && hasVisibleGameplay()) {
        window.__EDUPLAY_QUICK_PREVIEW_MARK_STARTED();
      }
    } catch (e) {}
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', lateBootstrap);
  } else {
    window.setTimeout(lateBootstrap, 0);
  }
})();
</script>"""

    head_content = script + "\n" + early_style
    head_open = re.search(r"<head\b[^>]*>", html, flags=re.IGNORECASE)
    if head_open:
        head_body_start = head_open.end()
        head_body = html[head_body_start:]
        head_close = re.search(r"</head>", head_body, flags=re.IGNORECASE)
        if head_close:
            head_body = head_body[:head_close.start()]
        charset_meta = re.search(
            r"<meta\b(?=[^>]*\bcharset\s*=)[^>]*>"
            r"|<meta\b(?=[^>]*\bhttp-equiv\s*=\s*['\"]?\s*content-type\b)"
            r"(?=[^>]*\bcontent\s*=)[^>]*>",
            head_body,
            flags=re.IGNORECASE,
        )
        insert_at = head_body_start + (charset_meta.end() if charset_meta else 0)
        html = html[:insert_at] + "\n" + head_content + html[insert_at:]
    elif re.search(r"</head>", html, flags=re.IGNORECASE):
        html = re.sub(
            r"</head>",
            head_content + "\n</head>",
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        html_open = re.search(r"<html\b[^>]*>", html, flags=re.IGNORECASE)
        if html_open:
            insert_at = html_open.end()
            html = html[:insert_at] + "\n<head>" + head_content + "</head>" + html[insert_at:]
        else:
            html = "<head>" + head_content + "</head>\n" + html

    body_end = """<script>
  var _installQuickPreviewQuestionTextOverride = function () {
    try {
      if (window.__EDUPLAY_QUICK_PREVIEW_AUTO_START &&
          typeof window.getDisplayQuestionText === 'function' &&
          !window.getDisplayQuestionText.__EDUPLAY_QUICK_PREVIEW_RAW) {
        var originalGetDisplayQuestionText = window.getDisplayQuestionText;
        var quickPreviewGetDisplayQuestionText = function (question) {
          try {
            if (typeof getRuntimeQuestionText === 'function') {
              var runtimeText = getRuntimeQuestionText(question);
              var rawText = String(runtimeText == null ? '' : runtimeText).trim();
              return rawText || '___';
            }
          } catch (e) {
            console.warn('[Preview] Could not read raw question text:', e);
          }
          return originalGetDisplayQuestionText.apply(this, arguments);
        };
        quickPreviewGetDisplayQuestionText.__EDUPLAY_QUICK_PREVIEW_RAW = true;
        window.getDisplayQuestionText = quickPreviewGetDisplayQuestionText;
      }
    } catch (e) {
      console.warn('[Preview] Could not install raw question text override:', e);
    }
  };
  _installQuickPreviewQuestionTextOverride();
  var _stripQuickPreviewQuestionPrefix = function (value) {
    var text = String(value == null ? '' : value).trim();
    if (!text) { return '___'; }
    text = text.replace(
      /^(?:(?:\\s*(?:câu|cau|question|q|pregunta|frage)\\s*(?:hỏi|hoi|so)?(?:\\s+số)?\\s*\\d+\\s*[:.\\-]?\\s*))+/i,
      ''
    ).trim();
    return text || '___';
  };
  var _installQuickPreviewFishingQuestionTextOverride = function () {
    try {
      if (window.__EDUPLAY_QUICK_PREVIEW_AUTO_START &&
          typeof window.getFishingQuestionText === 'function' &&
          !window.getFishingQuestionText.__EDUPLAY_QUICK_PREVIEW_FISHING_RAW) {
        var originalGetFishingQuestionText = window.getFishingQuestionText;
        var quickPreviewGetFishingQuestionText = function (question) {
          var originalText;
          try {
            originalText = originalGetFishingQuestionText.apply(this, arguments);
          } catch (e) {
            console.warn('[Preview] Could not read fishing question text:', e);
            return originalGetFishingQuestionText.apply(this, arguments);
          }
          try {
            return _stripQuickPreviewQuestionPrefix(originalText);
          } catch (e) {
            console.warn('[Preview] Could not strip fishing question prefix:', e);
            return originalText;
          }
        };
        quickPreviewGetFishingQuestionText.__EDUPLAY_QUICK_PREVIEW_FISHING_RAW = true;
        window.getFishingQuestionText = quickPreviewGetFishingQuestionText;
      }
    } catch (e) {
      console.warn('[Preview] Could not install fishing question text override:', e);
    }
  };
  _installQuickPreviewFishingQuestionTextOverride();
  var _installQuickPreviewMillionaireQuestionObserver = function () {
    try {
      var questionElement = document.getElementById('question');
      if (!questionElement ||
          typeof MutationObserver !== 'function' ||
          questionElement.__EDUPLAY_QUICK_PREVIEW_MILLIONAIRE_OBSERVER) {
        return !!questionElement;
      }
      var observer = new MutationObserver(function () {
        try {
          var currentText = String(questionElement.textContent || '');
          var strippedText = _stripQuickPreviewQuestionPrefix(currentText);
          if (strippedText !== currentText) {
            questionElement.textContent = strippedText;
          }
        } catch (e) {
          console.warn('[Preview] Could not strip millionaire question prefix:', e);
        }
      });
      observer.observe(questionElement, {
        childList: true,
        characterData: true,
        subtree: true
      });
      questionElement.__EDUPLAY_QUICK_PREVIEW_MILLIONAIRE_OBSERVER = observer;
      return true;
    } catch (e) {
      console.warn('[Preview] Could not install millionaire question observer:', e);
      return false;
    }
  };

  window.addEventListener('load', function () {
    console.log('[Preview] Window load event fired');
    try {
      var introScreen = document.getElementById('intro-screen');
      if (introScreen) { introScreen.style.display = 'none'; }
      var gameWrapper = document.getElementById('game-wrapper');
      if (gameWrapper) { gameWrapper.style.display = 'flex'; }
      var gameContent = document.getElementById('game-content');
      if (gameContent) { gameContent.style.display = 'block'; }
      var gameOver = document.getElementById('game-over');
      if (gameOver) { gameOver.style.display = 'none'; }

      _installQuickPreviewQuestionTextOverride();
      _installQuickPreviewFishingQuestionTextOverride();

      console.log('[Preview] Calling startGame()');
      if (typeof startGame === 'function') {
        startGame();
      } else {
        var _startQuickPreviewFishing = function () {
          if (window.__EDUPLAY_QUICK_PREVIEW_FISHING_STARTED) { return true; }
          try {
            if (typeof initGame !== 'function' ||
                typeof showQuestion !== 'function' ||
                typeof questions === 'undefined' ||
                !Array.isArray(questions) ||
                !questions.length) {
              return false;
            }
            window.__EDUPLAY_QUICK_PREVIEW_FISHING_STARTED = true;
            if (typeof window.__EDUPLAY_QUICK_PREVIEW_MARK_STARTED === 'function') {
              window.__EDUPLAY_QUICK_PREVIEW_MARK_STARTED();
            }
            initGame();
            var fishingQuestionIndex = Number(
              window.__EDUPLAY_QUICK_PREVIEW_QUESTION_INDEX
            );
            if (!isFinite(fishingQuestionIndex) ||
                fishingQuestionIndex < 0 ||
                fishingQuestionIndex >= questions.length) {
              fishingQuestionIndex = 0;
            }
            gameActive = false;
            try {
              if (questions[fishingQuestionIndex] &&
                  typeof questions[fishingQuestionIndex].question !== 'undefined') {
                questions[fishingQuestionIndex].question =
                  _stripQuickPreviewQuestionPrefix(
                    questions[fishingQuestionIndex].question
                  );
              }
            } catch (e) {
              console.warn('[Preview] Could not strip fishing question prefix:', e);
            }
            showQuestion(fishingQuestionIndex);
            return true;
          } catch (error) {
            window.__EDUPLAY_QUICK_PREVIEW_FISHING_STARTED = false;
            console.warn('[Preview] Fishing quick preview start failed:', error);
            return false;
          }
        };
        var _fishingStartAttempts = 0;
        var _tryStartQuickPreviewFishing = function () {
          if (_startQuickPreviewFishing()) { return; }
          _fishingStartAttempts += 1;
          if (_fishingStartAttempts < 30) {
            setTimeout(_tryStartQuickPreviewFishing, 100);
          } else {
            console.warn('[Preview] Fishing quick preview start timed out');
          }
        };
        var _millionairePreviewCandidate =
          document.getElementById('playGameBtn') &&
          document.getElementById('introVideo') &&
          document.getElementById('gameWindow') &&
          typeof $ === 'function';
        if (_millionairePreviewCandidate) {
          var _isQuickPreviewMillionaireReady = function () {
            try {
              var millionaireWindow = document.getElementById('gameWindow');
              var millionaireQuestion = document.getElementById('question');
              if (!millionaireWindow || !millionaireQuestion) { return false; }
              var style = window.getComputedStyle ?
                window.getComputedStyle(millionaireWindow) : null;
              if (style && (style.display === 'none' || style.visibility === 'hidden')) {
                return false;
              }
              return String(millionaireQuestion.textContent || '').trim() !== '';
            } catch (e) {
              return false;
            }
          };
          var _startQuickPreviewMillionaire = function () {
            if (_isQuickPreviewMillionaireReady()) {
              var footerElement = document.querySelector('footer');
              var footerStyle = footerElement && window.getComputedStyle ?
                window.getComputedStyle(footerElement) : null;
              if (footerElement && footerStyle && footerStyle.display === 'none') {
                footerElement.style.display = 'block';
              }
              return true;
            }
            try {
              var playButton = document.getElementById('playGameBtn');
              var introVideo = document.getElementById('introVideo');
              var millionaireWindow = document.getElementById('gameWindow');
              if (!playButton || !introVideo || !millionaireWindow ||
                  typeof $ !== 'function') {
                return false;
              }
              _installQuickPreviewMillionaireQuestionObserver();
              if (!window.__EDUPLAY_QUICK_PREVIEW_MILLIONAIRE_STARTED) {
                window.__EDUPLAY_QUICK_PREVIEW_MILLIONAIRE_STARTED = true;
                fadeTime = 0;
                ['preloader', 'mainMenu', 'introVideo'].forEach(function (id) {
                  var element = document.getElementById(id);
                  if (element) { element.style.display = 'none'; }
                });
                millionaireWindow.style.display = 'block';
                var clickEvent = document.createEvent('MouseEvents');
                clickEvent.initEvent('click', true, true);
                playButton.dispatchEvent(clickEvent);
                try { introVideo.pause(); } catch (e) {}
                var endedEvent = document.createEvent('Event');
                endedEvent.initEvent('ended', false, false);
                introVideo.dispatchEvent(endedEvent);
              }
              return _isQuickPreviewMillionaireReady();
            } catch (error) {
              console.warn('[Preview] Millionaire quick preview start failed:', error);
              return false;
            }
          };
          var _millionaireStartAttempts = 0;
          var _tryStartQuickPreviewMillionaire = function () {
            if (_startQuickPreviewMillionaire()) {
              window.__EDUPLAY_QUICK_PREVIEW_MILLIONAIRE_RESOLVED = true;
              return;
            }
            _millionaireStartAttempts += 1;
            if (_millionaireStartAttempts < 30) {
              setTimeout(_tryStartQuickPreviewMillionaire, 100);
            } else {
              console.warn('[Preview] Millionaire quick preview start timed out');
            }
          };
          _tryStartQuickPreviewMillionaire();
        } else {
          _tryStartQuickPreviewFishing();
        }
      }

      var _previewAudioListenersInstalled = false;
      var _previewAudioTargets = function () {
        var targets = [];
        var seen = [];
        var add = function (audio) {
          if (!audio || typeof audio.play !== 'function' || seen.indexOf(audio) >= 0) { return; }
          seen.push(audio);
          targets.push(audio);
        };
        try {
          var audioElements = document.querySelectorAll('audio');
          for (var i = 0; i < audioElements.length; i++) {
            add(audioElements[i]);
          }
        } catch (e) {
          console.warn('[Preview] Could not enumerate audio elements:', e);
        }
        try {
          if (typeof bgm !== 'undefined') { add(bgm); }
        } catch (e) {}
        try {
          if (typeof audioMap !== 'undefined' && audioMap) {
            Object.keys(audioMap).forEach(function (key) { add(audioMap[key]); });
          }
        } catch (e) {
          console.warn('[Preview] Could not enumerate audio map:', e);
        }
        return targets;
      };
      var _previewBackgroundAudio = function () {
        var backgroundAudio = null;
        try {
          if (typeof bgm !== 'undefined' && bgm) { backgroundAudio = bgm; }
        } catch (e) {}
        try {
          if (!backgroundAudio &&
              typeof audioMap !== 'undefined' &&
              audioMap &&
              audioMap.bg_question) {
            backgroundAudio = audioMap.bg_question;
            try {
              if (typeof bgm !== 'undefined' && !bgm) { bgm = backgroundAudio; }
            } catch (e) {}
          }
        } catch (e) {
          console.warn('[Preview] Could not find background audio:', e);
        }
        return backgroundAudio;
      };
      var _confirmPreviewAudioPlayback = function (audio, initialTime) {
        return new Promise(function (resolve) {
          var settled = false;
          var timer = null;
          var finish = function (played) {
            if (settled) { return; }
            settled = true;
            if (timer) { clearTimeout(timer); }
            try {
              audio.removeEventListener('playing', checkProgress);
              audio.removeEventListener('timeupdate', checkProgress);
            } catch (e) {}
            resolve(played);
          };
          var checkProgress = function () {
            if (settled) { return; }
            try {
              var currentTime = Number(audio.currentTime);
              var progressed = isFinite(currentTime) &&
                (currentTime > initialTime + 0.01 ||
                 currentTime < initialTime - 0.01);
              if (!audio.paused && progressed) { finish(true); }
            } catch (e) {}
          };
          try {
            audio.addEventListener('playing', checkProgress);
            audio.addEventListener('timeupdate', checkProgress);
          } catch (e) {}
          timer = setTimeout(function () {
            checkProgress();
            finish(false);
          }, 250);
        });
      };

      var _removeAudioInteractionListeners = function () {
        if (!_previewAudioListenersInstalled) { return; }
        ['pointerdown', 'click', 'touchstart', 'keydown'].forEach(function (eventName) {
          document.removeEventListener(eventName, _enableAudioOnInteraction);
        });
        _previewAudioListenersInstalled = false;
      };
      var _enableAudioOnInteraction = function () {
        console.log('[Preview] User interaction detected, enabling audio');
        _enablePreviewAudio().then(function (played) {
          if (played === true) { _removeAudioInteractionListeners(); }
        });
      };
      var _installAudioInteractionListeners = function () {
        if (_previewAudioListenersInstalled) { return; }
        ['pointerdown', 'click', 'touchstart', 'keydown'].forEach(function (eventName) {
          document.addEventListener(eventName, _enableAudioOnInteraction);
        });
        _previewAudioListenersInstalled = true;
      };
      var _enablePreviewAudio = function () {
        var targets = _previewAudioTargets();
        var backgroundAudio = _previewBackgroundAudio();
        try {
          if (typeof setFeedbackSoundPoolsMuted === 'function') {
            setFeedbackSoundPoolsMuted(false);
          }
        } catch (e) {
          console.warn('[Preview] Could not unmute feedback sound pools:', e);
        }
        targets.forEach(function (audio) {
          try {
            if (audio.volume === 0) { audio.volume = 0.5; }
            audio.muted = false;
          } catch (error) {
            console.warn('[Preview] Audio unmute failed:', error);
          }
        });
        if (!backgroundAudio) { return Promise.resolve(null); }
        try {
          var initialTime = Number(backgroundAudio.currentTime);
          if (!isFinite(initialTime)) { initialTime = 0; }
          var result = backgroundAudio.play();
          return Promise.resolve(result).then(function () {
            return _confirmPreviewAudioPlayback(backgroundAudio, initialTime);
          }).catch(function (error) {
            console.warn('[Preview] Audio playback rejected:', error);
            return false;
          });
        } catch (error) {
          console.warn('[Preview] Audio playback failed:', error);
          return Promise.resolve(false);
        }
      };

      // Attempt to auto-play sound as soon as the preview opens. If the
      // browser/embedded view still blocks it (no user gesture yet), fall back
      // to starting playback on the first user interaction (button press).
      _enablePreviewAudio().then(function (played) {
        if (played === false) { _installAudioInteractionListeners(); }
      });
      // Giả lập gesture để Edge/WebView2 cho phép autoplay (như Chrome)
      setTimeout(function () {
        var _last = Date.now();
        document.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true, cancelable: true }));
        document.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        // Đợi một chút rồi thử phát âm thanh lại
        setTimeout(function () {
          try { _enablePreviewAudio().then(function (played) { if (played === true) console.log('[Preview] Audio played after gesture'); }); } catch (e) { console.warn('[Preview] Audio replay failed:', e); }
        }, 100);
      }, 400);
    } catch (e) {
      console.error('Không thể tự mở câu hỏi:', e);
    }
  });
</script>"""
    html = html.replace("</body>", body_end + "</body>")
    return html


def inject_preview_marker(html: str) -> str:
    """Mark HTML as a preview so embedded game audio is never muted.

    Sets ``window.__EDUPLAY_PREVIEW = true`` for BOTH quick and full previews.
    The generated game JS uses this flag (instead of the quick-only
    ``__EDUPLAY_QUICK_PREVIEW_AUTO_START``) to decide whether to create audio
    elements muted — in any preview we want sound to play immediately.

    *Idempotent*: re-injecting already-marked HTML is a no-op.
    """
    html = str(html or "")
    if not html:
        return html
    marker = 'window["__EDUPLAY_PREVIEW"] = true;'
    if marker in html:
        return html
    script = (
        '<script>try { window["__EDUPLAY_PREVIEW"] = true; } catch (e) {}</script>'
    )
    if "<head>" in html:
        html = html.replace("<head>", "<head>" + script, 1)
    elif "</head>" in html:
        html = html.replace("</head>", script + "</head>", 1)
    elif "<body>" in html:
        html = html.replace("<body>", script + "<body>", 1)
    elif "</body>" in html:
        html = html.replace("</body>", script + "</body>", 1)
    else:
        html = html + script
    return html


_PREVIEW_AUDIO_HELPER_JS = """
(function () {
  if (window.__EDUPLAY_AUDIO_HELPER_DONE) { return; }
  window.__EDUPLAY_AUDIO_HELPER_DONE = true;
  function _audioTargets() {
    var out = [], seen = [];
    function add(a){ if(!a||typeof a.play!=='function'||seen.indexOf(a)>=0) return; seen.push(a); out.push(a); }
    try { var els = document.querySelectorAll('audio'); for (var i=0;i<els.length;i++) { add(els[i]); } } catch(e){}
    try { if (typeof bgm !== 'undefined') { add(bgm); } } catch(e){}
    try { if (typeof audioMap !== 'undefined' && audioMap) { Object.keys(audioMap).forEach(function(k){ add(audioMap[k]); }); } } catch(e){}
    return out;
  }
  function _bg() {
    try { if (typeof bgm !== 'undefined' && bgm) { return bgm; } } catch(e){}
    try { if (typeof audioMap !== 'undefined' && audioMap && audioMap.bg_question) { return audioMap.bg_question; } } catch(e){}
    return null;
  }
  function _enable() {
    try { if (typeof setFeedbackSoundPoolsMuted === 'function') { setFeedbackSoundPoolsMuted(false); } } catch(e){}
    _audioTargets().forEach(function(a){ try { if (a.volume === 0) { a.volume = 0.5; } a.muted = false; } catch(e){} });
    var bg = _bg();
    if (!bg) { return; }
    try { bg.muted = false; if (bg.volume === 0) { bg.volume = 0.5; } var p = bg.play(); if (p && p.catch) { p.catch(function(){}); } } catch(e){}
  }
  function _onGesture(){ _enable(); }
  ['pointerdown','click','touchstart','keydown'].forEach(function(ev){ try { document.addEventListener(ev, _onGesture, { once: true }); } catch(e){} });
  _enable();
  // Giả lập gesture để Edge/WebView2 cho phép autoplay (như Chrome)
  setTimeout(function(){
    try {
      document.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true, cancelable: true }));
      document.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
    } catch(e){}
    setTimeout(_enable, 120);
  }, 400);
  // Game có thể tự mute bgm sau khi init (vd fishing line 3386) → re-enable định kỳ
  var _tries = 0;
  var _iv = setInterval(function(){
    _tries += 1;
    _enable();
    if (_tries >= 12) { try { clearInterval(_iv); } catch(e){} }
  }, 1000);
})();
"""


def inject_preview_audio_helper(html: str) -> str:
    """Inject the audio-unmute/autoplay helper into preview HTML.

    Unmutes and plays every game audio element (including the fishing game's
    pre-muted ``bgm``) and the background music, with a simulated gesture so
    Edge/WebView2 allows autoplay. Works for BOTH quick and full previews.

    *Idempotent*: re-injecting already-marked HTML is a no-op.
    """
    html = str(html or "")
    if not html:
        return html
    marker = "window.__EDUPLAY_AUDIO_HELPER_DONE"
    if marker in html:
        return html
    script = "<script>" + _PREVIEW_AUDIO_HELPER_JS.strip() + "</script>"
    if "</body>" in html:
        html = html.replace("</body>", script + "</body>", 1)
    else:
        html = html + script
    return html


def ensure_preview_placeholder_file(path: Path, *, title: str, lang: str = "vi") -> None:
    try:
        p = Path(path)
    except Exception:
        return
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    try:
        html = build_preview_placeholder_html(lang=lang, title=title)
        p.write_text(html, encoding="utf-8")
    except Exception:
        pass
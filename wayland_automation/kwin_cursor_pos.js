// kwin_cursor_pos.js
// KWin script to track cursor position and transmit coordinates over D-Bus to wayland-automation.

var lastCallTime = 0;

function sendPos() {
  callDBus(
    'net.mousePosition',
    '/commands',
    'net.mousePosition',
    'ReceiveMousePosition',
    '[' + workspace.cursorPos.x + ', ' + workspace.cursorPos.y + ']'
  );
}

// Send initial position immediately upon load
sendPos();

// Subscribe to mouse movement events throttled to ~60 FPS
workspace.cursorPosChanged.connect(function() {
  var currentTime = Date.now();
  if (currentTime - lastCallTime > 16) {
    sendPos();
    lastCallTime = currentTime;
  }
});


const banner = document.getElementById("new-order-banner");
const entryOverlay = document.getElementById("admin-entry-overlay");
const enterButton = document.getElementById("enter-admin-button");

let lastLatestId = null;
let notificationSoundEnabled = false;
let audioContext = null;

const shouldShowEntryOverlay = entryOverlay?.dataset.showEntry === "true";

function cleanAdminEntryQuery() {
  const url = new URL(window.location.href);
  if (url.searchParams.has("skip_entry") || url.searchParams.has("enter")) {
    url.searchParams.delete("skip_entry");
    url.searchParams.delete("enter");
    window.history.replaceState({}, "", url.pathname + url.search + url.hash);
  }
}

function hideEntryOverlay() {
  if (entryOverlay) {
    entryOverlay.classList.add("hidden");
  }
}

async function restoreNotificationSoundIfPossible() {
  if (sessionStorage.getItem("adminNotificationSoundEnabled") !== "1") {
    return;
  }

  notificationSoundEnabled = true;

  if (enterButton) {
    enterButton.textContent = "通知音：ON";
  }

  const context = getAudioContext();
  if (!context) {
    return;
  }

  try {
    if (context.state === "suspended") {
      await context.resume();
    }
  } catch (error) {
    // ブラウザが自動再開を止めた場合は、次回の入室画面で有効化し直す。
  }
}

function showBanner() {
  if (!banner) return;

  banner.classList.remove("hidden");
  document.body.classList.add("new-order-flash");

  setTimeout(() => {
    banner.classList.add("hidden");
    document.body.classList.remove("new-order-flash");
  }, 4200);
}

function getAudioContext() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;

  if (!AudioContextClass) {
    return null;
  }

  if (!audioContext) {
    audioContext = new AudioContextClass();
  }

  return audioContext;
}

function playTone(frequency, startTime, duration, volume) {
  const context = getAudioContext();
  if (!context) return;

  const oscillator = context.createOscillator();
  const gainNode = context.createGain();

  oscillator.type = "square";
  oscillator.frequency.setValueAtTime(frequency, startTime);

  gainNode.gain.setValueAtTime(0.001, startTime);
  gainNode.gain.exponentialRampToValueAtTime(volume, startTime + 0.02);
  gainNode.gain.exponentialRampToValueAtTime(0.001, startTime + duration);

  oscillator.connect(gainNode);
  gainNode.connect(context.destination);

  oscillator.start(startTime);
  oscillator.stop(startTime + duration + 0.03);
}

function playNotificationSound() {
  if (!notificationSoundEnabled) return;

  const context = getAudioContext();
  if (!context) return;

  const now = context.currentTime;

  // 少し強めの通知音。音声ファイルなしでブラウザ側で鳴らす。
  playTone(880, now, 0.16, 0.18);
  playTone(1046, now + 0.22, 0.16, 0.18);
  playTone(880, now + 0.44, 0.22, 0.2);
  playTone(1046, now + 0.9, 0.16, 0.16);
  playTone(880, now + 1.12, 0.24, 0.18);
}

async function enterAdminScreen() {
  const context = getAudioContext();

  if (context) {
    try {
      if (context.state === "suspended") {
        await context.resume();
      }
      notificationSoundEnabled = true;
      sessionStorage.setItem("adminNotificationSoundEnabled", "1");
      playNotificationSound();
    } catch (error) {
      // 音が有効化できなくても、管理画面には入れる。
      notificationSoundEnabled = false;
      alert("通知音を有効にできませんでした。音量・ミュート設定を確認してください。");
    }
  }

  if (entryOverlay) {
    entryOverlay.classList.add("hidden");
  }
}

async function checkActiveOrderCount() {
  try {
    const response = await fetch("/api/admin/active-order-count", { cache: "no-store" });
    if (!response.ok) return;

    const data = await response.json();
    const latestId = Number(data.latest_id || 0);

    if (lastLatestId === null) {
      lastLatestId = latestId;
      return;
    }

    if (latestId > lastLatestId) {
      lastLatestId = latestId;
      showBanner();
      playNotificationSound();

      // 注文一覧を最新化するため少し待ってから再読み込みする。
      // 直後に音を鳴らしてから更新するので、注文に気づきやすい。
      // 新規注文による自動更新では、入室画面を出さない。
      setTimeout(() => window.location.replace("/admin?skip_entry=1"), 1800);
    }
  } catch (error) {
    // 管理画面の一時的な通信失敗は無視する。
  }
}

if (!shouldShowEntryOverlay) {
  hideEntryOverlay();
  restoreNotificationSoundIfPossible();
}

cleanAdminEntryQuery();

if (enterButton) {
  enterButton.addEventListener("click", enterAdminScreen);
}

setInterval(checkActiveOrderCount, 2500);
checkActiveOrderCount();

#!/usr/bin/env bash
# Самопроверка APK на эмуляторе: установить, запустить в режиме smoke, дождаться итога,
# забрать журнал и снимки экрана. Использование: ci_smoke.sh APK ПАПКА_РЕЗУЛЬТАТОВ
set -u
APK="$1"
OUT="$2"
PKG=com.gfontconverter.app
mkdir -p "$OUT"
adb install -r "$APK" || exit 1
adb logcat -c
adb shell am start -n $PKG/.MainActivity --ez smoke true
result=""
for i in $(seq 1 240); do
  result=$(adb logcat -d -s GFONT_SMOKE:I | grep -o "GFONT_SMOKE RESULT: [A-Z]*" | tail -1)
  [ -n "$result" ] && break
  [ $((i % 12)) -eq 0 ] && echo "ждём самопроверку… $((i * 5)) с"
  sleep 5
done
adb logcat -d > "$OUT/logcat.txt"
adb exec-out screencap -p > "$OUT/screen_end.png"
adb pull /sdcard/Android/data/$PKG/files/smoke "$OUT/" >/dev/null 2>&1 || true
echo "---- журнал самопроверки ----"
adb logcat -d -s GFONT_SMOKE:I | sed 's/^.*GFONT_SMOKE: //'
echo "---- ошибки Python/приложения ----"
grep -E "GfontEngine|AndroidRuntime|python.stderr" "$OUT/logcat.txt" | tail -40
echo "итог: ${result:-нет ответа}"
[ "$result" = "GFONT_SMOKE RESULT: OK" ]

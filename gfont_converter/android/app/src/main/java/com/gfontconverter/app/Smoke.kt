package com.gfontconverter.app

import android.graphics.Bitmap
import android.graphics.Canvas
import android.util.Log
import android.view.View
import android.view.View.MeasureSpec
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/**
 * Самопроверка на устройстве/эмуляторе (без человека):
 *   adb shell am start -n com.gfontconverter.app/.MainActivity --ez smoke true
 * Конвертер: встроенный DejaVu Sans -> .gfont, самопроверка. Почерк: символы рисуются
 * настоящими событиями касания по осевым линиям образца, заполнение из похожих, экспорт,
 * самопроверка. Результат и снимки экрана — в Android/data/<пакет>/files/smoke/,
 * итог — строка «GFONT_SMOKE RESULT: OK» в журнале (logcat).
 */
class Smoke(private val act: MainActivity) {
    private val out = File(act.getExternalFilesDir(null), "smoke").apply { deleteRecursively(); mkdirs() }
    private val lines = mutableListOf<String>()

    fun start() = Thread({ run() }, "smoke").start()

    private fun log(s: String) {
        Log.i("GFONT_SMOKE", s)
        lines += s
        File(out, "smoke.txt").writeText(lines.joinToString("\n") + "\n")
    }

    private fun <T> ui(f: () -> T): T {
        var r: T? = null
        var err: Throwable? = null
        val l = CountDownLatch(1)
        act.runOnUiThread {
            try { r = f() } catch (e: Throwable) { err = e }
            l.countDown()
        }
        l.await(60, TimeUnit.SECONDS)
        err?.let { throw it }
        @Suppress("UNCHECKED_CAST")
        return r as T
    }

    /** Дождаться, пока движок выполнит всё из очереди и главный поток применит ответы. */
    private fun barrier() {
        val l = CountDownLatch(1)
        Engine.run { l.countDown() }
        l.await(300, TimeUnit.SECONDS)
        ui { }
        ui { }
    }

    private fun waitFor(what: String, secs: Int, cond: () -> Boolean) {
        val t0 = System.currentTimeMillis()
        while (!ui(cond)) {
            if (System.currentTimeMillis() - t0 > secs * 1000L) throw RuntimeException("не дождались: $what")
            Thread.sleep(100)
        }
    }

    private fun shot(v: View, name: String) {
        ui {
            val b = Bitmap.createBitmap(v.width.coerceAtLeast(1), v.height.coerceAtLeast(1), Bitmap.Config.ARGB_8888)
            v.draw(Canvas(b))
            File(out, name).outputStream().use { b.compress(Bitmap.CompressFormat.PNG, 100, it) }
        }
    }

    private fun shotDetached(v: View, w: Int, name: String) {
        ui {
            v.measure(MeasureSpec.makeMeasureSpec(w, MeasureSpec.EXACTLY), MeasureSpec.makeMeasureSpec(0, MeasureSpec.UNSPECIFIED))
            v.layout(0, 0, v.measuredWidth, v.measuredHeight)
            val b = Bitmap.createBitmap(v.measuredWidth, v.measuredHeight.coerceAtLeast(1), Bitmap.Config.ARGB_8888)
            v.draw(Canvas(b))
            File(out, name).outputStream().use { b.compress(Bitmap.CompressFormat.PNG, 100, it) }
        }
    }

    private fun run() {
        var ok = false
        try {
            log("версия: ${act.version}")
            // ---------------- конвертер
            val conv = ui { act.converter()!! }
            ui { conv.isSmoke = true }
            val font = File(act.filesDir, "resources/sample/DejaVuSans.ttf").absolutePath
            ui { conv.loadFont(font) }
            barrier(); barrier()
            Thread.sleep(500)
            shot(act.window.decorView, "01_converter.png")
            val convOut = File(out, "конвертер DejaVu.gfont")
            ui { conv.startSave(convOut, null) }
            waitFor("сохранение конвертера", 600) { conv.lastReport.isNotEmpty() }
            val v1 = Engine.callSync("validate", convOut.absolutePath)
            log("конвертер: файл ${convOut.length()} байт, самопроверка: ${if (v1.optBoolean("valid")) "OK" else "ОШИБКИ"}")
            shot(act.window.decorView, "02_converter_saved.png")

            // ---------------- свой почерк
            ui { act.select("draw") }
            waitFor("экран рисования", 120) { act.draw()?.isResumed == true }
            val draw = ui { act.draw()!! }
            barrier(); barrier(); barrier()
            Thread.sleep(500)
            for (ch in listOf("а", "А", "р", "й", "5", ",", "‑", "@")) {
                ui { draw.select(ch.codePointAt(0)) }
                barrier()
                shot(draw.canvas, "canvas_template_U+%04X.png".format(ch.codePointAt(0)))
            }
            val text = "Съешь же ещё этих мягких булок, да выпей чаю! 2025"
            val chars = (text + "аАрй5,@-иеNo").filter { !it.isWhitespace() }.toSet()
            var strokes = 0
            for (ch in chars) {
                val code = ch.code
                ui { draw.select(code) }
                barrier()
                val h = Engine.callSync("draw_hint", code)
                val ls: JSONArray = h.optJSONArray("lines") ?: JSONArray()
                for (i in 0 until ls.length()) {
                    val poly = ls.getJSONArray(i).toPoly()
                    val pts = if (poly.size <= 2) poly else densify(poly)
                    ui { draw.canvas.simulateStroke(pts) }
                    strokes++
                }
                barrier()
            }
            val st = Engine.callSync("draw_state")
            val counts = st.getJSONArray("counts")
            log("нарисовано касаниями: ${chars.size} символов, $strokes штрихов; в проекте: ${counts.getInt(0)}")
            if (counts.getInt(0) < chars.size - 2) throw RuntimeException("нарисовано меньше, чем ожидалось")
            for (ch in listOf("а", "й", "@")) {
                ui { draw.select(ch.codePointAt(0)) }
                barrier()
                shot(draw.canvas, "canvas_drawn_U+%04X.png".format(ch.codePointAt(0)))
            }
            val sim = Engine.callSync("draw_fill_similar").getJSONObject("candidates")
            ui { draw.review(sim, "из похожих", autoApply = true) }
            barrier(); barrier()
            log("заполнено из похожих: ${sim.length()}")
            ui { draw.select("ё".codePointAt(0)) }
            barrier(); barrier()
            Thread.sleep(300)
            shot(act.window.decorView, "03_draw_screen.png")

            // строка предпросмотра
            val pv = "Съешь же ещё этих мягких французских булок, да выпей чаю! №5 — ок"
            val r = Engine.callSync("draw_line", pv)
            val g = r.getJSONObject("glyphs")
            val map = mutableMapOf<String, List<FloatArray>?>()
            for (k in g.keys()) map[k] = if (g.isNull(k)) null else g.getJSONArray(k).toPolys()
            val lineView = ui { StrokeLineView(act).apply { set(pv, map) } }
            shotDetached(lineView, ui { act.window.decorView.width }, "04_preview_line.png")

            // экспорт
            val outFile = File(out, "мой почерк.gfont")
            ui { draw.lastExport = null; draw.export(outFile, JSONObject().put("smoke", true), null) }
            waitFor("экспорт", 600) { draw.lastExport != null }
            val ex = ui { draw.lastExport!! }
            log(ex.optString("text"))
            val v2 = Engine.callSync("validate", outFile.absolutePath)
            log("почерк: самопроверка ${if (v2.optBoolean("valid")) "OK" else "ОШИБКИ"}")
            val imp = Engine.callSync("draw_import_gfont", outFile.absolutePath)
            log("файл открыт в редакторе: ${imp.optInt("imported")} символов")
            ok = v1.optBoolean("valid") && v2.optBoolean("valid") && ex.optBoolean("valid") &&
                imp.optInt("imported") >= counts.getInt(0)
        } catch (e: Throwable) {
            log("ОШИБКА: " + Log.getStackTraceString(e))
        }
        log("GFONT_SMOKE RESULT: " + if (ok) "OK" else "FAIL")
    }

    /** Точки через каждые ~4 ед. клетки, с лёгким «дрожанием руки». */
    private fun densify(q: FloatArray): FloatArray {
        val outPts = ArrayList<Float>()
        val rnd = java.util.Random(q.size.toLong())
        var i = 0
        while (i + 3 < q.size) {
            val x0 = q[i]; val y0 = q[i + 1]; val x1 = q[i + 2]; val y1 = q[i + 3]
            val n = maxOf(1, (Math.hypot((x1 - x0).toDouble(), (y1 - y0).toDouble()) / 4).toInt())
            for (s in 0 until n) {
                val t = s.toFloat() / n
                outPts += x0 + (x1 - x0) * t + (rnd.nextGaussian() * 0.8).toFloat()
                outPts += y0 + (y1 - y0) * t + (rnd.nextGaussian() * 0.8).toFloat()
            }
            i += 2
        }
        outPts += q[q.size - 2]; outPts += q[q.size - 1]
        return outPts.toFloatArray()
    }
}

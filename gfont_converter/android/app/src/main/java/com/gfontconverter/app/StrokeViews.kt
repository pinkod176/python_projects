package com.gfontconverter.app

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.view.View
import kotlin.math.max

/** Координаты .gfont: базовая линия −85, высота заглавных 315, строчных ≈220 (как в движке). */
const val G_BASELINE = -85f
const val G_CAP = 315f
const val G_XHEIGHT = 220f

fun strokesPath(strokes: List<FloatArray>, ox: Float, oy: Float, k: Float, path: Path = Path()): Path {
    path.reset()
    for (s in strokes) {
        if (s.size < 2) continue
        path.moveTo(ox + s[0] * k, oy + s[1] * k)
        if (s.size == 2) path.lineTo(ox + s[0] * k + 0.01f, oy + s[1] * k)
        var i = 2
        while (i + 1 < s.size) {
            path.lineTo(ox + s[i] * k, oy + s[i + 1] * k)
            i += 2
        }
    }
    return path
}

fun inkPaint(color: Int, width: Float) = Paint(Paint.ANTI_ALIAS_FLAG).apply {
    this.color = color
    style = Paint.Style.STROKE
    strokeWidth = width
    strokeCap = Paint.Cap.ROUND
    strokeJoin = Paint.Join.ROUND
}

/**
 * Строка текста по штрихам .gfont (как в файле). Раскладка приблизительная:
 * ширина символа = ширина bbox + зазор. Ненарисованные — бледным системным шрифтом.
 */
class StrokeLineView(ctx: Context) : View(ctx) {
    var text: String = ""
    var glyphs: Map<String, List<FloatArray>?> = emptyMap()
    var pen = 9f
    var guides = true
    private val k get() = context.dp(30f) / G_CAP          // высота заглавных ≈ 30 dp
    private val gap = 35f
    private val space = 110f
    private val lineH = 620f
    private val top = 470f
    private val path = Path()
    private val fallback = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(110, 140, 140, 150) }

    fun set(text: String, glyphs: Map<String, List<FloatArray>?>) {
        this.text = text
        this.glyphs = glyphs
        requestLayout()
        invalidate()
    }

    private data class Item(val ch: String, val x: Float, val w: Float, val strokes: List<FloatArray>?, val x0: Float)

    private fun layout(widthPx: Int): List<List<Item>> {
        val maxW = max(200f, (widthPx - context.dp(16f)) / k)
        fallback.textSize = G_CAP * 1.3f * k
        val lines = mutableListOf(mutableListOf<Item>())
        var x = 20f
        for (word in text.split(" ")) {
            val items = mutableListOf<Item>()
            var wx = 0f
            var i = 0
            while (i < word.length) {
                val cp = word.codePointAt(i)
                val ch = String(Character.toChars(cp))
                i += Character.charCount(cp)
                val st = glyphs[ch]
                if (st.isNullOrEmpty()) {
                    val w = fallback.measureText(ch) / k
                    items += Item(ch, wx, w, null, 0f)
                    wx += w + gap
                } else {
                    var x0 = Float.MAX_VALUE
                    var x1 = -Float.MAX_VALUE
                    for (s in st) for (j in s.indices step 2) { x0 = minOf(x0, s[j]); x1 = maxOf(x1, s[j]) }
                    val w = max(x1 - x0, 1f)
                    items += Item(ch, wx, w, st, x0)
                    wx += w + gap
                }
            }
            if (x + wx > maxW && lines.last().isNotEmpty()) {
                lines += mutableListOf<Item>()
                x = 20f
            }
            lines.last().addAll(items.map { it.copy(x = x + it.x) })
            x += wx + space
        }
        return lines
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val w = MeasureSpec.getSize(widthMeasureSpec)
        val n = if (text.isEmpty()) 1 else layout(w).size
        setMeasuredDimension(w, (n * lineH * k + context.dp(8f)).toInt())
    }

    override fun onDraw(c: Canvas) {
        c.drawColor(Color.WHITE)
        if (text.isEmpty()) return
        val ink = inkPaint(Color.rgb(20, 20, 25), max(1f, pen * k))
        val g = Paint().apply { strokeWidth = 1f }
        for ((li, items) in layout(width).withIndex()) {
            val oy = context.dp(4f) + (li * lineH + top) * k
            if (guides) {
                g.color = Color.rgb(240, 150, 150); c.drawLine(0f, oy + G_BASELINE * k, width.toFloat(), oy + G_BASELINE * k, g)
                g.color = Color.rgb(160, 190, 240); c.drawLine(0f, oy + (G_BASELINE - G_XHEIGHT) * k, width.toFloat(), oy + (G_BASELINE - G_XHEIGHT) * k, g)
                g.color = Color.rgb(210, 210, 210); c.drawLine(0f, oy + (G_BASELINE - G_CAP) * k, width.toFloat(), oy + (G_BASELINE - G_CAP) * k, g)
            }
            for (it in items) {
                if (it.strokes == null) {
                    c.drawText(it.ch, it.x * k, oy + G_BASELINE * k, fallback)
                } else {
                    c.drawPath(strokesPath(it.strokes, (it.x - it.x0) * k, oy, k, path), ink)
                }
            }
        }
    }
}

/** Миниатюра символа: нарисованный глиф или бледный символ; точка статуса в углу. */
class GlyphThumbView(ctx: Context) : View(ctx) {
    var ch = ""
    var strokes: List<FloatArray>? = null
    var status = "empty"
    var auto = false
    var current = false
    private val path = Path()
    private val p = Paint(Paint.ANTI_ALIAS_FLAG)

    override fun onDraw(c: Canvas) {
        val s = width.toFloat()
        val dark = context.isDark()
        p.style = Paint.Style.FILL
        p.color = if (dark) Color.rgb(52, 52, 58) else Color.rgb(255, 254, 248)
        c.drawRect(0f, 0f, s, height.toFloat(), p)
        val k = s / 640f
        val oy = s * 0.70f - G_BASELINE * k
        val st = strokes
        if (!st.isNullOrEmpty()) {
            c.drawPath(strokesPath(st, s / 2, oy, k, path),
                inkPaint(if (dark) Color.rgb(235, 235, 240) else Color.rgb(25, 25, 35), max(1.5f, 11 * k)))
        } else {
            p.color = if (dark) Color.argb(120, 200, 200, 210) else Color.argb(110, 120, 120, 130)
            p.textSize = s * 0.5f
            p.textAlign = Paint.Align.CENTER
            c.drawText(ch, s / 2, s * 0.68f, p)
        }
        val mark = when {
            status == "drawn" && auto -> Color.rgb(70, 130, 210)
            status == "drawn" -> Color.rgb(60, 160, 90)
            status == "skipped" -> Color.rgb(150, 150, 150)
            else -> 0
        }
        if (mark != 0) {
            p.color = mark
            val r = s * 0.08f
            c.drawCircle(s - r - 3, r + 3, r, p)
        }
        p.style = Paint.Style.STROKE
        p.strokeWidth = if (current) context.dp(2.5f) else 1f
        p.color = if (current) Color.rgb(59, 111, 212) else if (dark) Color.rgb(90, 90, 100) else Color.rgb(200, 200, 205)
        c.drawRect(1f, 1f, s - 1, height - 1f, p)
    }
}

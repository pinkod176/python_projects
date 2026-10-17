package com.gfontconverter.app

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.view.MotionEvent
import android.view.View
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min

/**
 * Холст одного символа (координаты — единицы клетки, как в настольной версии).
 * Слои: бумага -> линии тетради -> шаблон-подсказка пунктиром (не входит в штрихи и
 * экспорт) -> осевая линия с порядком -> штрихи пользователя (уже обработанные, как в
 * файле) с номерами, началом и стрелкой направления.
 * Один палец/перо — штрих; касание без движения — точка; два пальца — масштаб и сдвиг.
 * В режиме «Правка точек» точку можно перетащить, долгое касание штриха — удалить его.
 * Давление пера не используется: в формате толщина постоянная.
 */
class DrawCanvasView(ctx: Context) : View(ctx) {
    interface Listener {
        fun onStroke(points: FloatArray, dot: Boolean)
        fun onBeginPoint(stroke: Int)
        fun onMovePoint(stroke: Int, point: Int, x: Float, y: Float, final: Boolean)
        fun onDeleteStroke(stroke: Int)
    }

    var listener: Listener? = null

    // ---- данные (из Python) ----
    var cellW = 820f
    var cellH = 900f
    var guides: List<Pair<String, Float>> = emptyList()
    var k = 0.83f                        // ед. .gfont на ед. клетки
    var cap = 380f
    var tplKind = "none"
    var tplPolys: List<FloatArray> = emptyList()
    var tplClosed = true
    var tplRect = RectF()
    var tplLabel = ""
    var hintLines: List<FloatArray> = emptyList()
    var hintDots: List<Boolean> = emptyList()
    var strokes: List<FloatArray> = emptyList()
    var dots: List<Boolean> = emptyList()
    var code = 0x430
    var variant = 0

    // ---- вид ----
    var showTemplate = true
    var showOrder = false
    var showGuides = true
    var opacity = 0.35f
    var pen = 9f
    var editMode = false

    private var scale = 0.6f
    private var offX = 0f
    private var offY = 0f
    private var autoFit = true

    // ---- ввод ----
    private var raw: ArrayList<Float>? = null
    private var rawPx = 0f
    private var lastX = 0f
    private var lastY = 0f
    private var downTime = 0L
    private var multi = false
    private var pinchDist = 0f
    private var pinchCx = 0f
    private var pinchCy = 0f
    private var drag: Pair<Int, Int>? = null
    private var dragSent = 0L
    private val longPress = Runnable { onLongPress() }

    private val path = Path()
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG)
    private val line = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE }
    private val textP = Paint(Paint.ANTI_ALIAS_FLAG).apply { textAlign = Paint.Align.CENTER }

    private inner class Colors(dark: Boolean) {
        val bg = if (dark) Color.rgb(38, 38, 42) else Color.rgb(232, 232, 236)
        val paper = if (dark) Color.rgb(52, 52, 58) else Color.rgb(255, 254, 248)
        val border = if (dark) Color.rgb(90, 90, 100) else Color.rgb(200, 200, 205)
        val ink = if (dark) Color.rgb(235, 235, 240) else Color.rgb(25, 25, 35)
        val template = if (dark) Color.rgb(205, 205, 215) else Color.rgb(95, 95, 105)
        val hint = if (dark) Color.rgb(150, 190, 255) else Color.rgb(60, 110, 210)
        val base = if (dark) Color.rgb(220, 120, 120) else Color.rgb(232, 140, 140)
        val xline = if (dark) Color.rgb(110, 150, 220) else Color.rgb(105, 145, 230)
        val capline = if (dark) Color.rgb(140, 140, 150) else Color.rgb(185, 185, 190)
        val extra = if (dark) Color.rgb(110, 110, 120) else Color.rgb(215, 215, 220)
        val text = if (dark) Color.rgb(170, 170, 180) else Color.rgb(120, 120, 130)
        val start = Color.rgb(40, 170, 80)
        val arrow = Color.rgb(230, 120, 30)
    }

    init {
        isFocusable = true
    }

    // ---------------------------------------------------------------- вид
    fun fit() {
        val m = context.dp(6f)
        val w = max(50f, width - 2 * m)
        val h = max(50f, height - 2 * m)
        scale = min(w / cellW, h / cellH)
        offX = (width - cellW * scale) / 2
        offY = (height - cellH * scale) / 2
        autoFit = true
        invalidate()
    }

    override fun onSizeChanged(w: Int, h: Int, ow: Int, oh: Int) {
        if (autoFit) fit()
    }

    fun toCellX(x: Float) = (x - offX) / scale
    fun toCellY(y: Float) = (y - offY) / scale
    fun toViewX(x: Float) = offX + x * scale
    fun toViewY(y: Float) = offY + y * scale

    // ---------------------------------------------------------------- рисование
    override fun onDraw(c: Canvas) {
        val col = Colors(context.isDark())
        c.drawColor(col.bg)
        c.save()
        c.translate(offX, offY)
        c.scale(scale, scale)
        fill.style = Paint.Style.FILL
        fill.color = col.paper
        c.drawRect(0f, 0f, cellW, cellH, fill)
        line.pathEffect = null
        line.color = col.border
        line.strokeWidth = 1f / scale
        c.drawRect(0f, 0f, cellW, cellH, line)
        if (showGuides) drawGuides(c, col)
        if (showTemplate) drawTemplate(c, col)
        if (showOrder) drawHint(c, col)
        drawStrokes(c, col)
        c.restore()
        textP.textAlign = Paint.Align.LEFT
        textP.color = col.text
        textP.textSize = context.dp(13f)
        c.drawText("${String(Character.toChars(code))}   U+%04X   вариант ${variant + 1}".format(code),
            toViewX(10f), toViewY(0f) + context.dp(18f), textP)
        textP.textAlign = Paint.Align.CENTER
    }

    private fun drawGuides(c: Canvas, col: Colors) {
        val px = 1f / scale
        for ((name, y) in guides) {
            val (color, w, dashed) = when (name) {
                "base" -> Triple(col.base, 2f, false)
                "x" -> Triple(col.xline, 1.6f, false)
                "cap" -> Triple(col.capline, 1.2f, false)
                else -> Triple(col.extra, 1.2f, true)
            }
            line.color = color
            line.strokeWidth = w * px
            line.pathEffect = if (dashed) DashPathEffect(floatArrayOf(6 * px, 5 * px), 0f) else null
            c.drawLine(0f, y, cellW, y, line)
        }
        line.pathEffect = null
    }

    private fun polyPath(polys: List<FloatArray>, closed: Boolean): Path {
        path.reset()
        for (q in polys) {
            if (q.size < 2) continue
            path.moveTo(q[0], q[1])
            if (q.size == 2) path.lineTo(q[0] + 0.5f, q[1])
            var i = 2
            while (i + 1 < q.size) { path.lineTo(q[i], q[i + 1]); i += 2 }
            if (closed) path.close()
        }
        return path
    }

    private fun drawTemplate(c: Canvas, col: Colors) {
        if (tplKind == "none") return
        val a = (255 * opacity.coerceIn(0.05f, 1f)).toInt()
        line.color = col.template
        line.alpha = a
        line.strokeWidth = 2.4f                                  // ед. клетки: масштабируется с холстом
        line.strokeCap = Paint.Cap.BUTT
        line.pathEffect = DashPathEffect(floatArrayOf(9.6f, 6.4f), 0f)
        if (tplKind == "box") {
            c.drawRect(tplRect, line)
            textP.color = col.template
            textP.alpha = a
            textP.textSize = tplRect.height() * 0.6f
            c.drawText(tplLabel, tplRect.centerX(), tplRect.centerY() + textP.textSize * 0.35f, textP)
            textP.alpha = 255
        } else {
            c.drawPath(polyPath(tplPolys, tplClosed), line)
        }
        line.pathEffect = null
        line.alpha = 255
        line.strokeCap = Paint.Cap.ROUND
    }

    private fun drawHint(c: Canvas, col: Colors) {
        val a = (255 * (opacity + 0.3f).coerceIn(0.35f, 1f)).toInt()
        for ((i, q) in hintLines.withIndex()) {
            line.color = col.hint
            line.alpha = a
            line.strokeWidth = 1.8f
            line.pathEffect = DashPathEffect(floatArrayOf(5f, 5f), 0f)
            if (hintDots.getOrElse(i) { false } || q.size < 4) {
                c.drawCircle(q[0], q[1], 6f, line)
            } else {
                c.drawPath(polyPath(listOf(q), false), line)
                arrow(c, q, col.hint, 0.05f * cap, a)
            }
            line.pathEffect = null
            badge(c, q[0], q[1], (i + 1).toString(), col.hint, 0.045f * cap, filled = false, col = col)
        }
        line.alpha = 255
    }

    private fun arrow(c: Canvas, q: FloatArray, color: Int, size: Float, alpha: Int = 255) {
        val n = q.size / 2
        if (n < 2) return
        val ex = q[2 * n - 2]
        val ey = q[2 * n - 1]
        var j = n - 2
        while (j > 0 && hypot(q[2 * j] - ex, q[2 * j + 1] - ey) < size * 0.8f) j--
        var dx = ex - q[2 * j]
        var dy = ey - q[2 * j + 1]
        val len = hypot(dx, dy)
        if (len < 1e-3f) return
        dx /= len; dy /= len
        val tx = ex + dx * size * 0.35f
        val ty = ey + dy * size * 0.35f
        val p = Path()
        p.moveTo(tx, ty)
        p.lineTo(tx - dx * size - dy * size * 0.55f, ty - dy * size + dx * size * 0.55f)
        p.lineTo(tx - dx * size + dy * size * 0.55f, ty - dy * size - dx * size * 0.55f)
        p.close()
        fill.color = color
        fill.alpha = alpha
        c.drawPath(p, fill)
        fill.alpha = 255
    }

    private fun badge(c: Canvas, x: Float, y: Float, s: String, color: Int, r: Float, filled: Boolean, col: Colors) {
        val cx = x - 1.6f * r
        val cy = y - 1.6f * r
        fill.color = if (filled) color else col.paper
        c.drawCircle(cx, cy, r, fill)
        line.color = color
        line.strokeWidth = max(1f, r * 0.15f)
        c.drawCircle(cx, cy, r, line)
        textP.color = if (filled) col.paper else color
        textP.textSize = r * 1.3f
        textP.isFakeBoldText = true
        c.drawText(s, cx, cy + r * 0.45f, textP)
        textP.isFakeBoldText = false
    }

    private fun drawStrokes(c: Canvas, col: Colors) {
        val w = pen / k
        val ink = inkPaint(col.ink, w)
        for (q in strokes) if (q.size >= 4) c.drawPath(polyPath(listOf(q), false), ink)
        for ((i, q) in strokes.withIndex()) {
            if (q.size < 4) continue
            fill.color = col.start
            c.drawCircle(q[0], q[1], 0.6f * w + 2, fill)
            if (!dots.getOrElse(i) { false }) arrow(c, q, col.arrow, max(16f, 1.6f * w))
            badge(c, q[0], q[1], (i + 1).toString(), col.arrow, 0.045f * cap, filled = true, col = col)
            if (editMode) {
                fill.color = col.paper
                line.color = col.hint
                line.strokeWidth = 1.5f / scale
                var j = 0
                while (j + 1 < q.size) {
                    c.drawCircle(q[j], q[j + 1], 5f / scale, fill)
                    c.drawCircle(q[j], q[j + 1], 5f / scale, line)
                    j += 2
                }
            }
        }
        val r = raw
        if (r != null && r.size >= 2) {
            val live = inkPaint(Color.argb(150, Color.red(col.ink), Color.green(col.ink), Color.blue(col.ink)), w)
            path.reset()
            path.moveTo(r[0], r[1])
            if (r.size == 2) path.lineTo(r[0] + 0.01f, r[1])
            var i = 2
            while (i + 1 < r.size) { path.lineTo(r[i], r[i + 1]); i += 2 }
            c.drawPath(path, live)
        }
    }

    // ---------------------------------------------------------------- касания
    private fun nearestPoint(x: Float, y: Float): Pair<Int, Int>? {
        var best = context.dp(24f)
        var arg: Pair<Int, Int>? = null
        for ((i, q) in strokes.withIndex()) {
            var j = 0
            while (j + 1 < q.size) {
                val d = hypot(toViewX(q[j]) - x, toViewY(q[j + 1]) - y)
                if (d < best) { best = d; arg = i to j / 2 }
                j += 2
            }
        }
        return arg
    }

    private fun nearestStroke(x: Float, y: Float): Int? {
        val p = nearestPoint(x, y) ?: return null
        return p.first
    }

    private fun onLongPress() {
        if (!editMode || multi) return
        val i = nearestStroke(lastX, lastY) ?: return
        drag = null
        performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS)
        listener?.onDeleteStroke(i)
    }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                parent?.requestDisallowInterceptTouchEvent(true)
                multi = false
                lastX = e.x; lastY = e.y
                downTime = e.eventTime
                if (editMode) {
                    val hit = nearestPoint(e.x, e.y)
                    if (hit != null) {
                        drag = hit
                        listener?.onBeginPoint(hit.first)
                    }
                    postDelayed(longPress, 600)
                } else {
                    raw = arrayListOf(toCellX(e.x), toCellY(e.y))
                    rawPx = 0f
                }
                invalidate()
            }
            MotionEvent.ACTION_POINTER_DOWN -> {
                // второй палец: это жест масштаба/сдвига, начатый штрих отменяется
                multi = true
                raw = null
                drag = null
                removeCallbacks(longPress)
                startPinch(e)
                invalidate()
            }
            MotionEvent.ACTION_MOVE -> {
                if (multi) {
                    if (e.pointerCount >= 2) pinch(e)
                    return true
                }
                if (hypot(e.x - lastX, e.y - lastY) > context.dp(6f)) removeCallbacks(longPress)
                val d = drag
                if (d != null) {
                    val now = e.eventTime
                    if (now - dragSent > 40) {
                        dragSent = now
                        listener?.onMovePoint(d.first, d.second, toCellX(e.x), toCellY(e.y), false)
                    }
                    lastX = e.x; lastY = e.y
                    return true
                }
                val r = raw ?: return true
                for (h in 0 until e.historySize) addRaw(r, e.getHistoricalX(h), e.getHistoricalY(h))
                addRaw(r, e.x, e.y)
                invalidate()
            }
            MotionEvent.ACTION_POINTER_UP -> {
                if (e.pointerCount - 1 >= 2) startPinch(e, e.actionIndex)
            }
            MotionEvent.ACTION_UP -> {
                removeCallbacks(longPress)
                val d = drag
                if (d != null) {
                    drag = null
                    listener?.onMovePoint(d.first, d.second, toCellX(e.x), toCellY(e.y), true)
                    return true
                }
                val r = raw
                raw = null
                if (r != null && !multi) {
                    val dot = rawPx < context.dp(3f)
                    listener?.onStroke(if (dot) floatArrayOf(r[0], r[1]) else r.toFloatArray(), dot)
                }
                invalidate()
            }
            MotionEvent.ACTION_CANCEL -> {
                removeCallbacks(longPress)
                raw = null
                drag = null
                invalidate()
            }
        }
        return true
    }

    private fun addRaw(r: ArrayList<Float>, x: Float, y: Float) {
        val d = hypot(x - lastX, y - lastY)
        if (d < 0.5f) return
        rawPx += d
        lastX = x; lastY = y
        r.add(toCellX(x)); r.add(toCellY(y))
    }

    private fun startPinch(e: MotionEvent, skip: Int = -1) {
        val ids = (0 until e.pointerCount).filter { it != skip }.take(2)
        if (ids.size < 2) return
        val (a, b) = ids
        pinchDist = hypot(e.getX(a) - e.getX(b), e.getY(a) - e.getY(b))
        pinchCx = (e.getX(a) + e.getX(b)) / 2
        pinchCy = (e.getY(a) + e.getY(b)) / 2
    }

    private fun pinch(e: MotionEvent) {
        val d = hypot(e.getX(0) - e.getX(1), e.getY(0) - e.getY(1))
        val cx = (e.getX(0) + e.getX(1)) / 2
        val cy = (e.getY(0) + e.getY(1)) / 2
        if (pinchDist > 10f) {
            val f = d / pinchDist
            val ns = (scale * f).coerceIn(0.1f, 8f)
            val ff = ns / scale
            offX = cx + (offX - pinchCx) * ff
            offY = cy + (offY - pinchCy) * ff
            scale = ns
        }
        pinchDist = d
        pinchCx = cx
        pinchCy = cy
        autoFit = false
        invalidate()
    }

    /** Нарисовать штрих настоящими событиями касания (точки — в единицах клетки); для самопроверки. */
    fun simulateStroke(cell: FloatArray) {
        val t0 = android.os.SystemClock.uptimeMillis()
        val n = cell.size / 2
        fun ev(action: Int, i: Int, t: Long): MotionEvent =
            MotionEvent.obtain(t0, t, action, toViewX(cell[2 * i]), toViewY(cell[2 * i + 1]), 0)
        fun send(e: MotionEvent) { dispatchTouchEvent(e); e.recycle() }
        send(ev(MotionEvent.ACTION_DOWN, 0, t0))
        for (i in 1 until n) send(ev(MotionEvent.ACTION_MOVE, i, t0 + 8L * i))
        send(ev(MotionEvent.ACTION_UP, n - 1, t0 + 8L * n + 8))
    }

}

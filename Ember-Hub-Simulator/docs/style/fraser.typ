// Fraser document style — reports and slides. Matches the "fraser" matplotlib style (Segoe UI, Okabe–Ito).
// Usage:  #import "fraser.typ": report, slides, slide, kpi
// ---------------------------------------------------------------------------------------------------

#let ink = rgb("#1b1f24")
#let muted = rgb("#5b6470")
#let rule-col = rgb("#d5dae1")
#let accent = rgb("#0072B2")      // Okabe–Ito blue (series 1 in plots)
#let accent2 = rgb("#D55E00")     // Okabe–Ito vermillion
#let tint = rgb("#eef4f9")
#let sans = ("Segoe UI", "Arial", "DejaVu Sans")

// Small shared pieces ----------------------------------------------------------------------------
#let kpi(value, label, unit: none, size: 15pt) = box(
  width: 100%, inset: (x: 10pt, y: 8pt), radius: 3pt, fill: tint,
  stack(spacing: 4pt,
    text(size: 7.5pt, fill: muted, weight: "semibold", tracking: 0.04em, upper(label)),
    text(size: size, weight: "semibold", fill: ink, value + if unit != none { text(size: size * 0.6, fill: muted, " " + unit) }),
  ),
)

#let _tables() = {
  set table(stroke: none, inset: (x: 6pt, y: 4pt))
  show table.cell.where(y: 0): set text(weight: "semibold")
}

// Report -----------------------------------------------------------------------------------------
#let report(
  title: "", subtitle: none, author: "Fraser McLellan", date: datetime.today(),
  meta: (:), abstract: none, body,
) = {
  set document(title: title, author: author)
  set page(
    paper: "a4", margin: (x: 22mm, top: 24mm, bottom: 22mm),
    header: context if counter(page).get().first() > 1 {
      set text(size: 7.5pt, fill: muted)
      grid(columns: (1fr, auto), title, author)
      v(-6pt); line(length: 100%, stroke: 0.4pt + rule-col)
    },
    footer: context if counter(page).get().first() > 1 {
      set text(size: 7.5pt, fill: muted)
      grid(columns: (1fr, auto), meta.at("Run", default: ""), counter(page).display("1"))
    },
  )
  set text(font: sans, size: 10pt, fill: ink, lang: "en", region: "gb")
  set par(justify: true, leading: 0.62em, spacing: 1.0em)
  set heading(numbering: "1.1")
  show heading: set text(fill: ink, weight: "bold")
  show heading.where(level: 1): it => { v(10pt); text(size: 13pt, it); v(2pt) }
  show heading.where(level: 2): it => { v(6pt); text(size: 11pt, it) }
  set math.equation(numbering: "(1)")
  show math.equation: set text(font: "New Computer Modern Math")
  set figure(gap: 8pt)
  show figure.caption: it => align(left, text(size: 8.5pt, fill: muted,
    [#text(weight: "semibold", fill: ink, [#it.supplement #context it.counter.display(it.numbering).]) #it.body]))
  show figure.where(kind: table): set figure.caption(position: top)
  set table(stroke: (x, y) => (top: if y == 0 { 0.8pt + ink } else if y == 1 { 0.5pt + ink } else { 0pt },
                               bottom: 0.8pt + ink), inset: (x: 6pt, y: 4.5pt))
  show table.cell.where(y: 0): set text(weight: "semibold")
  set table(align: (x, y) => if x == 0 { left } else { right })
  show link: set text(fill: accent)
  show ref: set text(fill: accent)

  // Title block
  block(width: 100%, inset: (bottom: 10pt), stroke: (bottom: 2pt + accent), {
    text(size: 22pt, weight: "bold", title)
    if subtitle != none { v(-8pt); text(size: 12pt, fill: muted, subtitle) }
  })
  v(4pt)
  grid(columns: (auto, 1fr), column-gutter: 14pt, row-gutter: 5pt,
    ..((("Author", author), ("Date", date.display("[day] [month repr:long] [year]"))) + meta.pairs())
      .map(((k, v)) => (text(size: 8.5pt, fill: muted, k), text(size: 8.5pt, v))).flatten())
  if abstract != none {
    v(10pt)
    block(fill: tint, inset: 10pt, radius: 3pt, width: 100%,
      [#text(weight: "semibold", size: 9pt, "Summary") \ #text(size: 9.5pt, abstract)])
  }
  v(6pt)
  body
}

// Slides (16:9, no external packages) ------------------------------------------------------------
#let slides(title: "", author: "Fraser McLellan", date: datetime.today(), body) = {
  set document(title: title, author: author)
  set page(width: 254mm, height: 142.875mm, margin: (x: 16mm, top: 14mm, bottom: 12mm),
    footer: context {
      set text(size: 8pt, fill: muted)
      grid(columns: (1fr, auto), title, counter(page).display("1"))
    })
  set text(font: sans, size: 15pt, fill: ink, lang: "en", region: "gb")
  set par(leading: 0.6em)
  show math.equation: set text(font: "New Computer Modern Math")
  set list(marker: text(fill: accent, "■"), body-indent: 8pt, spacing: 10pt)
  body
}

#let title-slide(title, subtitle: none, author: "Fraser McLellan", date: datetime.today()) = page(footer: none, {
  v(1fr)
  text(size: 30pt, weight: "bold", title)
  if subtitle != none { v(-10pt); text(size: 17pt, fill: muted, subtitle) }
  v(6pt); line(length: 60mm, stroke: 3pt + accent); v(6pt)
  text(size: 12pt, fill: muted, author + "  ·  " + date.display("[day] [month repr:long] [year]"))
  v(1.2fr)
})

#let slide(title, body) = page({
  text(size: 22pt, weight: "bold", title)
  v(-6pt); line(length: 100%, stroke: 0.6pt + rule-col); v(8pt)
  block(width: 100%, height: 1fr, body)
})

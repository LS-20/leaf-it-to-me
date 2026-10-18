import SwiftUI

/// The remixed recipe: every ingredient line, swapped lines rewritten, then "why" and notes.
struct ResultView: View {
    let result: RemixResult
    @EnvironmentObject var app: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            recipeCard
            if !result.swaps.isEmpty { whyCard.id("why") }
            if !result.nutrientFlags.isEmpty || !result.warnings.isEmpty { notesCard }
        }
    }

    // MARK: recipe
    private var recipeCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(result.title).font(.pixel(22)).foregroundStyle(Color.ink)
            HStack(spacing: 6) {
                if let c = result.topCuisine { badge("\(c) cuisine", .pink) }
                badge(result.mode, .card)
                let fromPantry = result.swaps.filter(\.inPantry).count
                if fromPantry > 0 { badge("\(fromPantry) from your pantry", .sky) }
            }
            if result.swaps.isEmpty {
                Text("This dish already fits a \(result.mode) diet. Nothing to swap!").font(.body(14, .bold))
                    .padding(12).frame(maxWidth: .infinity, alignment: .leading).sticker(.greenSoft, shadow: 3, line: 2)
            } else {
                Text("\(result.swaps.count) swap\(result.swaps.count == 1 ? "" : "s"), highest impact first. Tap one to see why.")
                    .font(.body(12)).foregroundStyle(Color.muted)
            }
            VStack(spacing: 8) {
                ForEach(Array(result.before.enumerated()), id: \.offset) { _, item in
                    if let i = result.swaps.firstIndex(where: { $0.from == item.name }) {
                        swapRow(result.swaps[i], index: i)
                    } else {
                        plainRow(item)
                    }
                }
            }
            impact
        }
        .padding(16).sticker()
    }

    private func plainRow(_ item: Item) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text("\(Int(item.grams)) g").font(.body(12)).foregroundStyle(Color.muted).frame(width: 52, alignment: .trailing)
            Text(item.name).font(.body(15)).foregroundStyle(Color.ink)
            if item.diet == "check" && result.mode != "flexitarian" {
                Text("check label").font(.pixel(10)).foregroundStyle(Color.coral)
                    .padding(.horizontal, 6).padding(.vertical, 2)
                    .background(RoundedRectangle(cornerRadius: 5).fill(Color.coralSoft))
            }
            Spacer()
        }
        .padding(.vertical, 4)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.ink.opacity(0.12)).frame(height: 1) }
    }

    private func swapRow(_ s: Swap, index: Int) -> some View {
        let selected = app.selectedSwap == index
        return Button {
            withAnimation(.snappy) { app.selectedSwap = index }
        } label: {
            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text("\(Int(s.grams)) g").font(.body(12)).foregroundStyle(Color.muted).frame(width: 52, alignment: .trailing)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(s.from).font(.body(13)).foregroundStyle(Color.muted).strikethrough(true, color: .coral)
                        HStack(spacing: 6) {
                            Text(s.to.pretty).font(.pixel(19)).foregroundStyle(Color.ink)
                            if s.inPantry { pill("in your pantry", .sky) }
                            if s.userChoice { pill("your pick", .card) }
                        }
                    }
                }
                HStack(spacing: 12) {
                    meter("dish fit", s.fit)
                    if result.cuisineLock, let c = result.topCuisine { meter(c, s.cuisineFit) }
                    if selected { Text("why? ↓").font(.pixel(11)).foregroundStyle(Color.ink) }
                }
                .padding(.leading, 60)
                if !s.alternatives.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 6) {
                            Text("or").font(.body(12)).foregroundStyle(Color.muted)
                            ForEach(s.alternatives, id: \.name) { alt in
                                Button { Task { await app.choose(alt.name, for: s.from) } } label: {
                                    Text((alt.inPantry ? "✓ " : "") + alt.name.pretty).font(.body(12, .bold)).foregroundStyle(Color.ink)
                                        .padding(.horizontal, 10).padding(.vertical, 5)
                                        .background(Capsule().fill(Color.card)).overlay(Capsule().stroke(Color.ink, lineWidth: 2))
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                    .padding(.leading, 60)
                }
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .buttonStyle(.plain)
        .sticker(selected ? .mint : .greenSoft, radius: 12, shadow: selected ? 4 : 3, line: 2)
    }

    @ViewBuilder private var impact: some View {
        let b = result.footprintBefore.ghg, a = result.footprintAfter.ghg
        if b - a > 0.05 {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text("−\(Int(((b - a) / b * 100).rounded()))% CO₂").font(.pixel(20)).foregroundStyle(Color.ink)
                Text(String(format: "%.1f → %.1f kg", b, a) + (b - a > 0.5 ? " · ≈\(Int(((b - a) / 0.4).rounded())) mi of driving" : ""))
                    .font(.body(12)).foregroundStyle(Color.muted)
            }
            .padding(12).frame(maxWidth: .infinity, alignment: .leading)
            .sticker(.amberSoft, radius: 12, shadow: 3, line: 2)
        }
    }

    // MARK: why
    private var whyCard: some View {
        let s = result.swaps[min(app.selectedSwap, result.swaps.count - 1)]
        return VStack(alignment: .leading, spacing: 12) {
            Text("Why these swaps?").font(.pixel(18)).foregroundStyle(Color.ink)
            FlavorGraphView(graph: result.graph, swap: s).frame(maxWidth: .infinity)
            legend
            whyText(s)
            Text("Lines join ingredients Epicure places close together; thicker means closer. Drag a node to move it. Faded nodes were removed.")
                .font(.body(11)).foregroundStyle(Color.muted)
        }
        .padding(16).sticker()
    }

    private var legend: some View {
        let groups = Array(Set(result.graph.nodes.map(\.group))).sorted()
        let names = ["protein": "Protein", "dairy": "Dairy & egg", "spice": "Spice & herb", "vegetable": "Vegetable",
                     "grain": "Grain", "sauce": "Sauce", "fat": "Fat & oil", "fruit": "Fruit & nut"]
        return FlowLayout(spacing: 10) {
            ForEach(groups, id: \.self) { g in
                HStack(spacing: 4) {
                    Rectangle().fill(Color.group(g)).frame(width: 9, height: 9).overlay(Rectangle().stroke(Color.ink, lineWidth: 1))
                    Text(names[g] ?? g).font(.pixel(10, .semibold)).foregroundStyle(Color.ink)
                }
            }
        }
    }

    private func whyText(_ s: Swap) -> some View {
        let names = s.why.map(\.name.pretty)
        let list = names.count > 1 ? names.dropLast().joined(separator: ", ") + " and " + names.last! : names.joined()
        var text = AttributedString(s.to.pretty)
        text.font = .pixel(15); text.foregroundColor = .green
        var rest = AttributedString(" replaces \(s.from) because Epicure links it closely with ")
        rest.font = .body(14)
        var why = AttributedString(list)
        why.font = .body(14, .heavy); why.foregroundColor = .amber
        var tail = AttributedString(", which are already in your dish." + (result.cuisineLock && result.topCuisine != nil ? " It also leans \(result.topCuisine!), like the rest of the dish." : ""))
        tail.font = .body(14)
        return Text(text + rest + why + tail).foregroundStyle(Color.ink)
    }

    // MARK: notes
    private var notesCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            if !result.nutrientFlags.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Nutrients to watch").font(.pixel(15)).foregroundStyle(Color.ink)
                    Text("not medical advice").font(.body(11)).foregroundStyle(Color.muted)
                    ForEach(result.nutrientFlags, id: \.self) { n in
                        (Text(n.nutrient).font(.body(13, .heavy)) + Text(": \(n.tip)").font(.body(13))).foregroundStyle(Color.ink)
                    }
                }
                .padding(12).frame(maxWidth: .infinity, alignment: .leading).sticker(.amberSoft, radius: 12, shadow: 0, line: 2)
            }
            if !result.warnings.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Check these").font(.pixel(15)).foregroundStyle(Color.ink)
                    ForEach(result.warnings, id: \.self) { Text("• " + $0).font(.body(13)).foregroundStyle(Color.ink) }
                }
                .padding(12).frame(maxWidth: .infinity, alignment: .leading).sticker(.coralSoft, radius: 12, shadow: 0, line: 2)
            }
        }
        .padding(16).sticker()
    }

    // MARK: bits
    private func badge(_ text: String, _ fill: Color) -> some View {
        Text(text).font(.pixel(11, .semibold)).foregroundStyle(Color.ink)
            .padding(.horizontal, 9).padding(.vertical, 4)
            .background(Capsule().fill(fill)).overlay(Capsule().stroke(Color.ink, lineWidth: 2))
    }
    private func pill(_ text: String, _ fill: Color) -> some View {
        Text(text).font(.pixel(10)).foregroundStyle(Color.ink)
            .padding(.horizontal, 6).padding(.vertical, 2)
            .background(RoundedRectangle(cornerRadius: 5).fill(fill)).overlay(RoundedRectangle(cornerRadius: 5).stroke(Color.ink, lineWidth: 1.5))
    }
    private func meter(_ label: String, _ value: Double) -> some View {
        HStack(spacing: 4) {
            Text(label).font(.body(10)).foregroundStyle(Color.muted)
            ZStack(alignment: .leading) {
                Rectangle().fill(Color.card).frame(width: 44, height: 7)
                Rectangle().fill(Color.leaf).frame(width: 44 * max(0, min(1, value)), height: 7)
            }
            .overlay(Rectangle().stroke(Color.ink, lineWidth: 1.2))
        }
    }
}

/// "How accurate is it?" — same numbers as the web app.
struct AccuracyCard: View {
    let bench: BenchModel
    @State private var shown = false
    @State private var expanded = false

    var body: some View {
        let rows: [(String, Double, Bool)] = [
            ("Leaf It To Me", bench.hit("ours_cuisine_lock"), true),
            ("Closest to the meat", bench.hit("nearest_to_meat"), false),
            ("\"Just use tofu\"", bench.hit("always_tofu"), false),
            ("Random pick", bench.hit("random"), false),
        ]
        VStack(alignment: .leading, spacing: 10) {
            Text("How accurate is it?").font(.pixel(18)).foregroundStyle(Color.ink)
            Text("We wrote down the plant protein used by the well-known plant-based version of \(bench.nDishes) meat dishes before testing, then checked how often each method picks it first.")
                .font(.body(12)).foregroundStyle(Color.muted)
            ForEach(rows, id: \.0) { label, v, ours in
                HStack(spacing: 8) {
                    Text(label).font(ours ? .pixel(12) : .body(12)).foregroundStyle(Color.ink).frame(width: 120, alignment: .leading)
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            Rectangle().fill(Color.card)
                            Rectangle().fill(ours ? Color.leaf : Color.beige).frame(width: geo.size.width * (shown ? v : 0))
                        }
                        .overlay(Rectangle().stroke(Color.ink, lineWidth: 2))
                    }
                    .frame(height: 16)
                    Text("\(Int((v * 100).rounded()))%").font(ours ? .pixel(12) : .body(12, .bold)).foregroundStyle(Color.ink).frame(width: 36, alignment: .trailing)
                }
            }
            DisclosureGroup(isExpanded: $expanded) {
                VStack(alignment: .leading, spacing: 3) {
                    ForEach(bench.rows, id: \.self) { r in
                        Text(rowText(r)).font(.body(12)).foregroundStyle(Color.ink)
                    }
                }
                .padding(.top, 6)
            } label: {
                Text("See all \(bench.nDishes) dishes").font(.pixel(12)).foregroundStyle(Color.ink)
            }
            .tint(Color.ink)
        }
        .padding(16).sticker()
        .onAppear { withAnimation(.easeOut(duration: 1).delay(0.2)) { shown = true } }
    }

    private func rowText(_ r: BenchRow) -> String {
        let mark = r.hit1 ? "✓ " : "✗ "
        let picked: String = (r.oursTop3.first ?? "").pretty
        let expected: String = r.gold.map { $0.pretty }.joined(separator: " or ")
        let tail: String = r.hit1 ? "" : " (expected \(expected))"
        return mark + r.dish + ": " + picked + tail
    }
}

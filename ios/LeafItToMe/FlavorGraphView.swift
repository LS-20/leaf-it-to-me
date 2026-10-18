import SwiftUI

/// Force-directed "flavor graph" of the remixed dish, styled like an arcade screen.
/// Same idea as the web app: the selected swap sits in the centre, lime links show
/// which dish ingredients explain it, removed ingredients are faded ghosts.
struct FlavorGraphView: View {
    let graph: FlavorGraph
    let swap: Swap?
    @State private var positions: [String: CGPoint] = [:]
    @State private var dragging: String?

    private let size = CGSize(width: 320, height: 340)

    var body: some View {
        let why = Set(swap?.why.map(\.name) ?? [])
        let focus = swap?.to
        let old = swap?.fromEpicure
        let lit: (String) -> Bool = { $0 == focus || $0 == old || why.contains($0) }
        let center = CGPoint(x: size.width / 2, y: size.height / 2)

        ZStack {
            Color.screen
            // edges
            ForEach(edgeList(focus: focus, why: why), id: \.self) { e in
                let isWhy = e.kind == "pair" && ((e.a == focus && why.contains(e.b)) || (e.b == focus && why.contains(e.a)))
                let isFocusSwap = e.kind == "swap" && e.a == old && e.b == focus
                EdgeLine(from: positions[e.a] ?? center, to: positions[e.b] ?? center)
                    .stroke(isWhy || isFocusSwap ? Color.mint : Color(hex: 0x3a4036),
                            style: StrokeStyle(lineWidth: e.kind == "swap" ? 1.5 : (isWhy ? 4 : 1 + max(0, e.w - 0.35) * 8),
                                               lineCap: .round, dash: e.kind == "swap" ? [4, 5] : []))
                    .opacity(focus == nil || isWhy || isFocusSwap ? 1 : 0.5)
            }
            // nodes
            ForEach(graph.nodes, id: \.id) { n in
                let isFocus = n.id == focus
                VStack(spacing: 4) {
                    ZStack {
                        Circle().fill(Color.group(n.group).opacity(n.kind == "removed" ? 0.3 : 1))
                        Circle().stroke(isFocus ? Color.mint : Color.ink,
                                        style: StrokeStyle(lineWidth: isFocus ? 3 : 2, dash: n.kind == "removed" ? [3, 3] : []))
                        if n.kind == "new" { Text("+").font(.pixel(isFocus ? 16 : 11)).foregroundStyle(.white) }
                    }
                    .frame(width: radius(n, focus) * 2, height: radius(n, focus) * 2)
                    .shadow(color: isFocus ? Color.mint.opacity(0.7) : .clear, radius: 8)
                    Text(n.label)
                        .font(.pixel(isFocus ? 12 : 10, isFocus ? .heavy : .semibold))
                        .strikethrough(n.kind == "removed")
                        .foregroundStyle(isFocus || (lit(n.id) && n.kind != "removed") ? Color.mint : Color(hex: 0xe9eee4))
                        .padding(.horizontal, 5).padding(.vertical, 2)
                        .background(RoundedRectangle(cornerRadius: 5).fill(Color(hex: 0x221e2e)))
                        .overlay(RoundedRectangle(cornerRadius: 5).stroke(Color(hex: 0x4a4360), lineWidth: 1))
                        .fixedSize()
                }
                .opacity(focus == nil || lit(n.id) ? 1 : 0.6)
                .opacity(n.kind == "removed" && !lit(n.id) ? 0.6 : 1)
                // VStack is centred on the node; shift so the circle (not the label) sits on the point
                .position(x: (positions[n.id] ?? center).x, y: (positions[n.id] ?? center).y + labelHeight(n, focus) / 2)
                .gesture(DragGesture().onChanged { v in
                    positions[n.id] = CGPoint(x: v.location.x, y: v.location.y - labelHeight(n, focus) / 2)
                })
            }
        }
        .frame(width: size.width, height: size.height)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.ink, lineWidth: 3))
        .onAppear { relayout(animated: true) }
        .onChange(of: swap?.to) { relayout(animated: true) }
        .onChange(of: graph.nodes.map(\.id)) { relayout(animated: true) }
    }

    private func radius(_ n: GraphNode, _ focus: String?) -> CGFloat {
        n.id == focus ? 17 : n.kind == "new" ? 12 : n.kind == "removed" ? 9 : 10
    }
    private func labelHeight(_ n: GraphNode, _ focus: String?) -> CGFloat { n.id == focus ? 22 : 19 }
    private func labelWidth(_ n: GraphNode, _ focus: String?) -> CGFloat {
        CGFloat(n.label.count) * (n.id == focus ? 7.6 : 6.4) + 14
    }

    /// Graph edges plus explicit links from the selected swap to its "why" ingredients.
    private func edgeList(focus: String?, why: Set<String>) -> [GraphEdge] {
        var edges = graph.edges
        if let focus, let swap {
            for w in swap.why where graph.nodes.contains(where: { $0.id == w.name }) {
                if !edges.contains(where: { ($0.a == focus && $0.b == w.name) || ($0.b == focus && $0.a == w.name) }) {
                    edges.append(GraphEdge(a: focus, b: w.name, w: w.sim, kind: "pair"))
                }
            }
        }
        return edges
    }

    private func relayout(animated: Bool) {
        let target = layout()
        if positions.isEmpty {
            // start everything in the middle, then spring outwards
            positions = Dictionary(uniqueKeysWithValues: graph.nodes.map { ($0.id, CGPoint(x: size.width / 2, y: size.height / 2)) })
        }
        if animated { withAnimation(.spring(response: 0.7, dampingFraction: 0.75)) { positions = target } } else { positions = target }
    }

    /// Simple force simulation (repulsion, springs, gravity) + box collisions so labels never overlap.
    private func layout() -> [String: CGPoint] {
        let focus = swap?.to
        let W = size.width, H = size.height
        struct N { var id: String; var x: CGFloat; var y: CGFloat; var vx: CGFloat = 0; var vy: CGFloat = 0
                   var bw: CGFloat; var top: CGFloat; var bot: CGFloat; var pinned: Bool }
        var nodes: [N] = graph.nodes.enumerated().map { i, n in
            let a = CGFloat(i) * 2.39996, r = 30 + 9 * CGFloat(i)
            let rad = radius(n, focus)
            return N(id: n.id, x: W / 2 + cos(a) * r, y: H / 2 + sin(a) * r,
                     bw: max(rad * 2, labelWidth(n, focus)) + 6, top: rad + 3,
                     bot: rad + 4 + labelHeight(n, focus) + 3, pinned: n.id == focus)
        }
        let index = Dictionary(uniqueKeysWithValues: nodes.enumerated().map { ($0.element.id, $0.offset) })
        let edges = edgeList(focus: focus, why: Set(swap?.why.map(\.name) ?? [])).compactMap { e -> (Int, Int, GraphEdge)? in
            guard let s = index[e.a], let t = index[e.b] else { return nil }
            return (s, t, e)
        }
        for i in nodes.indices where nodes[i].pinned { nodes[i].x = W / 2; nodes[i].y = H / 2 - 10 }

        func collide() {
            for i in nodes.indices {
                for j in nodes.indices where j > i {
                    let a = nodes[i], b = nodes[j]
                    let ac = a.y + (a.bot - a.top) / 2, bc = b.y + (b.bot - b.top) / 2
                    let ox = (a.bw + b.bw) / 2 - abs(b.x - a.x)
                    let oy = (a.top + a.bot + b.top + b.bot) / 2 - abs(bc - ac)
                    guard ox > 0, oy > 0 else { continue }
                    let share: (CGFloat, CGFloat) = a.pinned ? (0, 1) : b.pinned ? (1, 0) : (0.5, 0.5)
                    if ox < oy {
                        let s: CGFloat = b.x >= a.x ? 1 : -1
                        nodes[i].x -= s * ox * share.0; nodes[j].x += s * ox * share.1
                    } else {
                        let s: CGFloat = bc >= ac ? 1 : -1
                        nodes[i].y -= s * oy * share.0; nodes[j].y += s * oy * share.1
                    }
                }
            }
            for i in nodes.indices where !nodes[i].pinned {
                nodes[i].x = min(W - nodes[i].bw / 2, max(nodes[i].bw / 2, nodes[i].x))
                nodes[i].y = min(H - nodes[i].bot, max(nodes[i].top, nodes[i].y))
            }
        }

        var heat: CGFloat = 1
        for _ in 0..<320 {
            for i in nodes.indices {
                for j in nodes.indices where j > i {
                    var dx = nodes[j].x - nodes[i].x, dy = nodes[j].y - nodes[i].y
                    let d2 = dx * dx + dy * dy + 0.01, d = sqrt(d2)
                    let f = 3200 / d2 * heat
                    dx /= d; dy /= d
                    nodes[i].vx -= dx * f; nodes[i].vy -= dy * f
                    nodes[j].vx += dx * f; nodes[j].vy += dy * f
                }
            }
            for (s, t, e) in edges {
                let dx = nodes[t].x - nodes[s].x, dy = nodes[t].y - nodes[s].y
                let d = max(1, sqrt(dx * dx + dy * dy))
                let rest: CGFloat = e.kind == "swap" ? 60 : min(130, max(60, 70 + 120 * (0.85 - e.w)))
                let k = (e.kind == "swap" ? 0.04 : 0.02 + e.w * 0.04) * heat * (d - rest) / d
                nodes[s].vx += dx * k; nodes[s].vy += dy * k
                nodes[t].vx -= dx * k; nodes[t].vy -= dy * k
            }
            for i in nodes.indices {
                nodes[i].vx += (W / 2 - nodes[i].x) * 0.004 * heat
                nodes[i].vy += (H / 2 - nodes[i].y) * 0.004 * heat
                nodes[i].vx *= 0.55; nodes[i].vy *= 0.55
                if nodes[i].pinned { nodes[i].vx = 0; nodes[i].vy = 0; continue }
                nodes[i].x += nodes[i].vx; nodes[i].y += nodes[i].vy
            }
            heat *= 0.985
            collide()
        }
        for _ in 0..<60 { collide() }
        return Dictionary(uniqueKeysWithValues: nodes.map { ($0.id, CGPoint(x: $0.x, y: $0.y)) })
    }
}

/// A line whose ends animate smoothly when node positions change.
struct EdgeLine: Shape {
    var from: CGPoint
    var to: CGPoint
    var animatableData: AnimatablePair<AnimatablePair<CGFloat, CGFloat>, AnimatablePair<CGFloat, CGFloat>> {
        get { AnimatablePair(AnimatablePair(from.x, from.y), AnimatablePair(to.x, to.y)) }
        set { from = CGPoint(x: newValue.first.first, y: newValue.first.second)
              to = CGPoint(x: newValue.second.first, y: newValue.second.second) }
    }
    func path(in rect: CGRect) -> Path {
        var p = Path(); p.move(to: from); p.addLine(to: to); return p
    }
}

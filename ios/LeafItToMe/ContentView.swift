import SwiftUI
import PhotosUI

struct ContentView: View {
    @StateObject private var app = AppState()
    @State private var tab = "samples"
    @State private var pasteText = ""
    @State private var recipePick: PhotosPickerItem?
    @State private var pantryPicks: [PhotosPickerItem] = []
    @State private var pantryInput = ""
    @State private var showSettings = false

    var body: some View {
        ZStack {
            DotGrid()
            ScrollViewReader { scroller in
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        header
                        recipeStep
                        pantryStep
                        dietStep
                        if let r = app.result {
                            ResultView(result: r).environmentObject(app).id("result")
                        } else {
                            emptyState
                        }
                        if let b = app.benchmark { AccuracyCard(bench: b) }
                        footer
                    }
                    .padding(16)
                    .padding(.bottom, 40)
                }
                .onChange(of: app.result?.title) {
                    withAnimation { scroller.scrollTo("result", anchor: .top) }
                    // Test hook: "-demoScroll why" jumps to the flavor graph.
                    let args = ProcessInfo.processInfo.arguments
                    if let i = args.firstIndex(of: "-demoScroll"), i + 1 < args.count {
                        let target = args[i + 1]
                        Task { try? await Task.sleep(nanoseconds: 600_000_000); withAnimation { scroller.scrollTo(target, anchor: .top) } }
                    }
                }
            }
            if let busy = app.busy { BusyOverlay(text: busy) }
            if let toast = app.toast {
                VStack { Spacer(); Text(toast).font(.body(14, .bold)).foregroundStyle(Color.bg).padding(12)
                    .background(RoundedRectangle(cornerRadius: 12).fill(Color.ink)).padding(.bottom, 24).padding(.horizontal, 16) }
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .animation(.snappy, value: app.toast)
        .task { await app.load() }
        .sheet(isPresented: $showSettings) { SettingsSheet() }
        .preferredColorScheme(.light)
    }

    // MARK: header
    private var header: some View {
        HStack(spacing: 12) {
            PixelSprite(name: "sprout", size: 48)
            VStack(alignment: .leading, spacing: 2) {
                Text("Leaf It To Me").font(.pixel(26)).foregroundStyle(Color.ink)
                    .shadow(color: .leaf, radius: 0, x: 2, y: 2)
                Text("Same dish, lighter footprint, still itself.").font(.body(13, .bold)).foregroundStyle(Color.muted)
            }
            Spacer()
            Button { showSettings = true } label: { Image(systemName: "gearshape.fill").foregroundStyle(Color.muted) }
                .accessibilityLabel("Server settings")
        }
    }

    // MARK: step 1
    private var recipeStep: some View {
        VStack(alignment: .leading, spacing: 12) {
            stepHead(1, "Your recipe", .pink)
            HStack(spacing: 6) {
                tabButton("samples", "Try a dish")
                tabButton("paste", "Text")
                tabButton("photo", "Photo")
            }
            switch tab {
            case "paste":
                TextEditor(text: $pasteText)
                    .font(.body(15)).frame(minHeight: 110).scrollContentBackground(.hidden)
                    .padding(8).background(RoundedRectangle(cornerRadius: 10).fill(Color.card))
                    .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color.ink, lineWidth: 2))
                Button { Task { await app.parseText(pasteText) } } label: {
                    Text("Read recipe with Gemini").font(.pixel(15)).foregroundStyle(Color.ink).frame(maxWidth: .infinity).padding(12)
                }.buttonStyle(PressStyle(fill: .sky))
            case "photo":
                PhotosPicker(selection: $recipePick, matching: .images) {
                    dropZone(sprite: "camera", title: "Pick a recipe photo", subtitle: "A recipe card or cookbook page")
                }
                .onChange(of: recipePick) {
                    guard let item = recipePick else { return }
                    Task {
                        if let data = try? await item.loadTransferable(type: Data.self), let img = UIImage(data: data) { await app.recipePhoto(img) }
                        recipePick = nil
                    }
                }
            default:
                LazyVGrid(columns: [GridItem(.flexible(), spacing: 10), GridItem(.flexible(), spacing: 10)], spacing: 12) {
                    ForEach(app.samples) { s in
                        Button { Task { await app.pickSample(s.key) } } label: {
                            VStack(alignment: .leading, spacing: 6) {
                                PixelSprite(name: Sprites.sampleSprite[s.key] ?? "curry", size: 40)
                                Text(s.title).font(.body(14, .bold)).foregroundStyle(Color.ink).multilineTextAlignment(.leading)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                            .frame(maxWidth: .infinity, minHeight: 86, alignment: .topLeading).padding(10)
                        }
                        .buttonStyle(PressStyle(fill: app.selectedSample == s.key ? .greenSoft : .card))
                    }
                }
            }
            if !app.ingredients.isEmpty { ingredientEditor }
        }
        .padding(16).sticker()
    }

    private var ingredientEditor: some View {
        VStack(alignment: .leading, spacing: 8) {
            Divider().overlay(Color.ink.opacity(0.3))
            Text(app.title).font(.pixel(16)).foregroundStyle(Color.ink)
            Text("Check the list. Fix anything that was misread.").font(.body(12)).foregroundStyle(Color.muted)
            ForEach($app.ingredients) { $ing in
                HStack(spacing: 6) {
                    TextField("Ingredient", text: $ing.name).font(.body(14)).textFieldStyle(.plain)
                        .padding(7).background(RoundedRectangle(cornerRadius: 8).fill(Color.card))
                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.ink, lineWidth: 1.5))
                    TextField("g", value: $ing.grams, format: .number).font(.body(14)).keyboardType(.decimalPad)
                        .multilineTextAlignment(.trailing).frame(width: 64)
                        .padding(7).background(RoundedRectangle(cornerRadius: 8).fill(Color.card))
                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.ink, lineWidth: 1.5))
                    Text("g").font(.body(12)).foregroundStyle(Color.muted)
                    Button { app.ingredients.removeAll { $0.id == ing.id } } label: {
                        Image(systemName: "xmark").font(.system(size: 12, weight: .bold)).foregroundStyle(Color.muted)
                    }
                }
            }
            Button("+ Add ingredient") { app.ingredients.append(Ingredient(name: "", grams: 100)) }
                .font(.pixel(13)).foregroundStyle(Color.green)
        }
    }

    // MARK: step 2
    private var pantryStep: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack { stepHead(2, "Your pantry", .sky); Text("optional").font(.body(11)).foregroundStyle(Color.muted) }
            Text("Show us your shelves. Swaps you already own get ranked first, so you buy less and waste less.")
                .font(.body(13)).foregroundStyle(Color.muted)
            PhotosPicker(selection: $pantryPicks, maxSelectionCount: 10, matching: .images) {
                dropZone(sprite: "can", title: "Snap your pantry, fridge & shelves", subtitle: "Add as many photos as you like")
            }
            .onChange(of: pantryPicks) {
                let picks = pantryPicks
                guard !picks.isEmpty else { return }
                Task {
                    var images: [UIImage] = []
                    for p in picks { if let d = try? await p.loadTransferable(type: Data.self), let i = UIImage(data: d) { images.append(i) } }
                    pantryPicks = []
                    await app.pantryPhotos(images)
                }
            }
            if app.pantryPhotos > 0 || !app.pantry.isEmpty {
                HStack {
                    PixelSprite(name: "camera", size: 18)
                    Text("\(app.pantryPhotos) photo\(app.pantryPhotos == 1 ? "" : "s") scanned · \(app.pantry.count) items")
                        .font(.body(12, .bold)).foregroundStyle(Color.ink)
                    Spacer()
                    Button("Clear") { app.pantry = []; app.pantryPhotos = 0; Task { await app.remixIfReady() } }
                        .font(.pixel(12)).foregroundStyle(Color.green)
                }
                FlowLayout(spacing: 6) {
                    ForEach(app.pantry, id: \.self) { item in
                        HStack(spacing: 4) {
                            Text(item).font(.body(12, .bold))
                            Button { app.pantry.removeAll { $0 == item }; Task { await app.remixIfReady() } } label: {
                                Image(systemName: "xmark").font(.system(size: 9, weight: .heavy))
                            }
                        }
                        .foregroundStyle(Color.ink).padding(.horizontal, 9).padding(.vertical, 5)
                        .background(Capsule().fill(Color.sky)).overlay(Capsule().stroke(Color.ink, lineWidth: 2))
                    }
                }
            }
            HStack(spacing: 8) {
                TextField("or type an item, e.g. chickpeas", text: $pantryInput).font(.body(14)).textFieldStyle(.plain)
                    .padding(9).background(RoundedRectangle(cornerRadius: 10).fill(Color.card))
                    .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color.ink, lineWidth: 2))
                    .onSubmit(addTyped)
                Button(action: addTyped) { Text("Add").font(.pixel(14)).foregroundStyle(Color.ink).padding(.horizontal, 12).padding(.vertical, 9) }
                    .buttonStyle(PressStyle(fill: .sky, radius: 10))
            }
        }
        .padding(16).sticker()
    }

    private func addTyped() {
        app.addPantry(pantryInput.split(separator: ",").map(String.init))
        pantryInput = ""
        Task { await app.remixIfReady() }
    }

    // MARK: step 3
    private var dietStep: some View {
        VStack(alignment: .leading, spacing: 12) {
            stepHead(3, "How plant-forward?", .mint)
            HStack(spacing: 6) {
                modeButton("pescetarian", "Pesce", "fish is ok")
                modeButton("vegetarian", "Veggie", "no meat/fish")
                modeButton("vegan", "Vegan", "all plants")
            }
            Toggle(isOn: $app.cuisineLock) {
                VStack(alignment: .leading, spacing: 1) {
                    Text("Cuisine lock").font(.pixel(14)).foregroundStyle(Color.ink)
                    Text("Keep swaps inside the dish's cuisine").font(.body(11)).foregroundStyle(Color.muted)
                }
            }
            .tint(.leaf)
            .onChange(of: app.cuisineLock) { Task { await app.remixIfReady() } }
            Button { Task { await app.remix() } } label: {
                Text("Remix it →").font(.pixel(20)).foregroundStyle(Color.ink).frame(maxWidth: .infinity).padding(14)
            }
            .buttonStyle(PressStyle(fill: .leaf))
            .disabled(app.ingredients.isEmpty)
            .opacity(app.ingredients.isEmpty ? 0.5 : 1)
        }
        .padding(16).sticker()
    }

    private var emptyState: some View {
        VStack(spacing: 10) {
            HStack(spacing: 14) {
                PixelSprite(name: "curry", size: 60)
                Text("→").font(.pixel(28)).foregroundStyle(Color.muted)
                PixelSprite(name: "sprout", size: 60)
            }
            Text("Pick a dish to begin").font(.pixel(18)).foregroundStyle(Color.ink)
            Text("We'll find plant-based swaps that fit its cuisine, show how much CO₂ you save, and flag anything to watch.")
                .font(.body(13)).foregroundStyle(Color.muted).multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity).padding(24).sticker()
    }

    private var footer: some View {
        Text("Swaps are plausible pairings from ingredient co-occurrence and flavor chemistry, not taste-tested. Footprints are global averages (Poore & Nemecek 2018). Nutrition notes are not medical advice. Built with Epicure (Radzikowski & Chen, KAIKAKU.AI, CC-BY-4.0) and Gemini.")
            .font(.body(11)).foregroundStyle(Color.muted)
    }

    // MARK: small pieces
    private func stepHead(_ n: Int, _ title: String, _ color: Color) -> some View {
        HStack(spacing: 10) { StepNumber(n: n, color: color); Text(title).font(.pixel(19)).foregroundStyle(Color.ink) }
    }

    private func tabButton(_ id: String, _ label: String) -> some View {
        Button { withAnimation(.snappy) { tab = id } } label: {
            Text(label).font(.pixel(13)).foregroundStyle(Color.ink).frame(maxWidth: .infinity).padding(.vertical, 8)
        }
        .buttonStyle(PressStyle(fill: tab == id ? .amberSoft : .card, radius: 10))
    }

    private func modeButton(_ id: String, _ label: String, _ hint: String) -> some View {
        Button {
            app.mode = id
            Task { await app.remixIfReady() }
        } label: {
            VStack(spacing: 2) {
                Text(label).font(.pixel(14))
                Text(hint).font(.body(10, .semibold)).foregroundStyle(Color.muted)
            }
            .foregroundStyle(Color.ink).frame(maxWidth: .infinity).padding(.vertical, 9)
        }
        .buttonStyle(PressStyle(fill: app.mode == id ? .mint : .card, radius: 10))
    }

    private func dropZone(sprite: String, title: String, subtitle: String) -> some View {
        HStack(spacing: 12) {
            PixelSprite(name: sprite, size: 34)
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.body(14, .heavy)).foregroundStyle(Color.ink)
                Text(subtitle).font(.body(12)).foregroundStyle(Color.muted)
            }
            .multilineTextAlignment(.leading)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: 12).fill(Color.card))
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.ink, style: StrokeStyle(lineWidth: 2.5, dash: [6, 4])))
    }
}

struct BusyOverlay: View {
    let text: String
    @State private var spin = false
    var body: some View {
        ZStack {
            Color.bg.opacity(0.75).ignoresSafeArea()
            VStack(spacing: 14) {
                PixelSprite(name: "sprout", size: 56)
                    .rotationEffect(.degrees(spin ? 8 : -8))
                    .animation(.easeInOut(duration: 0.4).repeatForever(autoreverses: true), value: spin)
                Text(text).font(.pixel(14)).foregroundStyle(Color.ink).multilineTextAlignment(.center)
            }
            .padding(24).sticker()
            .padding(40)
        }
        .onAppear { spin = true }
    }
}

struct SettingsSheet: View {
    @AppStorage("server") private var server = ""
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("http://127.0.0.1:8000", text: $server)
                        .keyboardType(.URL).textInputAutocapitalization(.never).autocorrectionDisabled()
                } header: { Text("Server address") } footer: {
                    Text("The simulator uses this Mac's server automatically. On a phone, enter your computer's address on the same wifi, e.g. http://192.168.1.20:8000.")
                }
            }
            .navigationTitle("Settings")
            .toolbar { Button("Done") { dismiss() } }
        }
    }
}

/// Wrapping row layout for pantry chips.
struct FlowLayout: Layout {
    var spacing: CGFloat = 6
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxW = proposal.width ?? .infinity
        var x: CGFloat = 0, y: CGFloat = 0, rowH: CGFloat = 0, widest: CGFloat = 0
        for s in subviews {
            let sz = s.sizeThatFits(.unspecified)
            if x + sz.width > maxW, x > 0 { x = 0; y += rowH + spacing; rowH = 0 }
            x += sz.width + spacing; rowH = max(rowH, sz.height); widest = max(widest, x)
        }
        return CGSize(width: min(widest, maxW), height: y + rowH)
    }
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, rowH: CGFloat = 0
        for s in subviews {
            let sz = s.sizeThatFits(.unspecified)
            if x + sz.width > bounds.maxX, x > bounds.minX { x = bounds.minX; y += rowH + spacing; rowH = 0 }
            s.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(sz))
            x += sz.width + spacing; rowH = max(rowH, sz.height)
        }
    }
}

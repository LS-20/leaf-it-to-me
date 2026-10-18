import SwiftUI
import UIKit

@MainActor
final class AppState: ObservableObject {
    @Published var samples: [Sample] = []
    @Published var selectedSample: String?
    @Published var title = ""
    @Published var ingredients: [Ingredient] = []
    @Published var pantry: [String] = []
    @Published var pantryPhotos = 0
    @Published var mode = "vegan"
    @Published var model = "core"
    @Published var cuisineLock = true
    @Published var overrides: [String: String] = [:]
    @Published var result: RemixResult?
    @Published var selectedSwap = 0
    @Published var benchmark: BenchModel?
    @Published var busy: String?
    @Published var toast: String?

    func load() async {
        do {
            samples = try await API.samples()
            benchmark = try await API.benchmark()["core"]
            // Test hook: launch with "-demoSample butter_chicken" to open a dish (optionally "-demoSwap 1").
            let args = ProcessInfo.processInfo.arguments
            if let m = args.firstIndex(of: "-demoMode"), m + 1 < args.count { mode = args[m + 1] }
            if let i = args.firstIndex(of: "-demoSample"), i + 1 < args.count {
                await pickSample(args[i + 1])
                if let j = args.firstIndex(of: "-demoSwap"), j + 1 < args.count, let n = Int(args[j + 1]) { selectedSwap = n }
            }
        } catch {
            show("Can't reach the server at \(API.baseURL.absoluteString). Is it running?")
        }
    }

    func show(_ message: String) {
        toast = message
        Task { try? await Task.sleep(nanoseconds: 3_500_000_000); if toast == message { toast = nil } }
    }

    private func setRecipe(_ r: Recipe) async {
        title = r.title ?? "Your recipe"
        ingredients = r.ingredients
        overrides = [:]
        selectedSwap = 0
        await remix()
    }

    func pickSample(_ key: String) async {
        selectedSample = key
        do { await setRecipe(try await API.sample(key)) } catch { show(error.localizedDescription) }
    }

    func parseText(_ text: String) async {
        busy = "Gemini is reading your recipe…"
        defer { busy = nil }
        do { selectedSample = nil; await setRecipe(try await API.parseText(text)) } catch { show(error.localizedDescription) }
    }

    func recipePhoto(_ image: UIImage) async {
        busy = "Gemini is reading your recipe photo…"
        defer { busy = nil }
        do { selectedSample = nil; await setRecipe(try await API.photo(image, kind: "recipe", as: Recipe.self)) }
        catch { show(error.localizedDescription) }
    }

    /// Read every pantry photo in parallel and merge the items (no duplicates).
    func pantryPhotos(_ images: [UIImage]) async {
        guard !images.isEmpty else { return }
        busy = images.count > 1 ? "Gemini is looking at \(images.count) photos…" : "Gemini is looking at your pantry…"
        defer { busy = nil }
        var found: [String] = []
        var ok = 0
        await withTaskGroup(of: [String]?.self) { group in
            for img in images {
                group.addTask { try? await API.photo(img, kind: "pantry", as: PantryItems.self).items }
            }
            for await items in group { if let items { ok += 1; found += items } }
        }
        let before = pantry.count
        addPantry(found)
        pantryPhotos += ok
        let failed = images.count - ok
        show("Found \(pantry.count - before) new items in \(ok) photo\(ok == 1 ? "" : "s")." + (failed > 0 ? " \(failed) couldn't be read." : ""))
        await remixIfReady()
    }

    func addPantry(_ items: [String]) {
        var seen = Set(pantry.map { $0.lowercased() })
        for raw in items {
            let t = raw.trimmingCharacters(in: .whitespaces)
            if !t.isEmpty, !seen.contains(t.lowercased()) { pantry.append(t); seen.insert(t.lowercased()) }
        }
    }

    func remixIfReady() async { if result != nil { await remix() } }

    func choose(_ alternative: String, for original: String) async {
        overrides[original] = alternative
        await remix()
    }

    func remix() async {
        let items = ingredients.filter { !$0.name.trimmingCharacters(in: .whitespaces).isEmpty }
        guard !items.isEmpty else { return }
        let body = RemixRequest(title: title, ingredients: items, mode: mode, model: model,
                                cuisineLock: cuisineLock, pantry: pantry, overrides: overrides)
        do {
            let r = try await API.remix(body)
            withAnimation(.snappy) {
                result = r
                if selectedSwap >= r.swaps.count { selectedSwap = 0 }
            }
        } catch { show(error.localizedDescription) }
    }
}

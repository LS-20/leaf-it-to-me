import Foundation

// Shapes match the server's JSON (see docs/API.md). Snake_case keys are converted automatically.

struct Sample: Codable, Identifiable, Hashable {
    let key: String
    let title: String
    var id: String { key }
}

struct Ingredient: Codable, Identifiable, Hashable {
    var id = UUID()
    var name: String
    var grams: Double

    enum CodingKeys: String, CodingKey { case name, grams }
}

struct Recipe: Codable {
    var title: String?
    var ingredients: [Ingredient]
}

struct PantryItems: Codable { let items: [String] }

struct RemixRequest: Encodable {
    let title: String
    let ingredients: [Ingredient]
    let mode: String
    let model: String
    let cuisineLock: Bool
    let pantry: [String]
    let overrides: [String: String]
}

struct CuisineScore: Decodable {
    let name: String
    let score: Double
    init(from decoder: Decoder) throws {           // JSON is ["South_Asian", 0.92]
        var c = try decoder.unkeyedContainer()
        name = try c.decode(String.self)
        score = try c.decode(Double.self)
    }
}

struct Alternative: Decodable, Hashable {
    let name: String
    let fit: Double
    let cuisineFit: Double
    let inPantry: Bool
}

struct Why: Decodable, Hashable {
    let name: String
    let sim: Double
}

struct Swap: Decodable, Identifiable {
    let from: String
    let fromEpicure: String
    let grams: Double
    let to: String
    let fit: Double
    let cuisineFit: Double
    let inPantry: Bool
    let userChoice: Bool
    let alternatives: [Alternative]
    let why: [Why]
    var id: String { from }
}

struct Item: Decodable {
    let name: String
    let grams: Double
    let epicure: String?
    let diet: String
}

struct Footprint: Decodable {
    let ghg: Double
    let coverage: Double
}

struct NutrientFlag: Decodable, Hashable {
    let nutrient: String
    let lostFrom: [String]
    let tip: String
}

struct GraphNode: Decodable, Hashable {
    let id: String
    let label: String
    let group: String
    let kind: String          // kept | new | removed
}

struct GraphEdge: Decodable, Hashable {
    let a: String
    let b: String
    let w: Double
    let kind: String          // pair | swap
}

struct FlavorGraph: Decodable {
    let nodes: [GraphNode]
    let edges: [GraphEdge]
}

struct RemixResult: Decodable {
    let title: String
    let mode: String
    let cuisine: [CuisineScore]
    let cuisineLock: Bool
    let swaps: [Swap]
    let before: [Item]
    let after: [Item]
    let footprintBefore: Footprint
    let footprintAfter: Footprint
    let nutrientFlags: [NutrientFlag]
    let warnings: [String]
    let graph: FlavorGraph

    var topCuisine: String? { cuisine.first?.name.replacingOccurrences(of: "_", with: " ") }
}

struct BenchHit: Decodable { let hitAt1: Double; let hitAt3: Double }
struct BenchRow: Decodable, Hashable { let dish: String; let hit1: Bool; let oursTop3: [String]; let gold: [String] }
struct BenchModel: Decodable {
    let nDishes: Int
    let summary: [String: BenchHit]
    let rows: [BenchRow]
    // Dictionary keys may or may not be converted from snake_case; accept both.
    func hit(_ key: String) -> Double {
        let camel = key.split(separator: "_").enumerated()
            .map { $0.offset == 0 ? String($0.element) : $0.element.capitalized }.joined()
        return (summary[key] ?? summary[camel])?.hitAt1 ?? 0
    }
}

extension String {
    /// Epicure names use underscores ("chana_dal"); show them with spaces.
    var pretty: String { replacingOccurrences(of: "_", with: " ") }
}

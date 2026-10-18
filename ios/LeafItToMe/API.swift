import Foundation
import UIKit

/// Talks to the Leaf It To Me server (the same one the web app uses).
/// The simulator can reach the Mac's server at 127.0.0.1; on a real phone, set the
/// server address in Settings to your computer's address on the same wifi.
enum API {
    static var baseURL: URL {
        let saved = UserDefaults.standard.string(forKey: "server") ?? ""
        return URL(string: saved.isEmpty ? "http://127.0.0.1:8000" : saved) ?? URL(string: "http://127.0.0.1:8000")!
    }

    struct ServerError: LocalizedError {
        let message: String
        var errorDescription: String? { message }
    }

    private static let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()
    private static let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        return e
    }()

    private static func send<T: Decodable>(_ req: URLRequest, as: T.Type) async throws -> T {
        let (data, resp) = try await URLSession.shared.data(for: req)
        if let http = resp as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            let detail = (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["detail"] as? String
            throw ServerError(message: detail ?? "Server error (\(http.statusCode))")
        }
        return try decoder.decode(T.self, from: data)
    }

    private static func get<T: Decodable>(_ path: String, as type: T.Type) async throws -> T {
        try await send(URLRequest(url: baseURL.appendingPathComponent(path)), as: type)
    }

    private static func post<T: Decodable, B: Encodable>(_ path: String, body: B, as type: T.Type) async throws -> T {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try encoder.encode(body)
        req.timeoutInterval = 60
        return try await send(req, as: type)
    }

    static func samples() async throws -> [Sample] { try await get("api/samples", as: [Sample].self) }
    static func sample(_ key: String) async throws -> Recipe { try await get("api/samples/\(key)", as: Recipe.self) }
    static func benchmark() async throws -> [String: BenchModel] { try await get("api/benchmark", as: [String: BenchModel].self) }

    static func parseText(_ text: String) async throws -> Recipe {
        try await post("api/parse/text", body: ["text": text], as: Recipe.self)
    }

    static func remix(_ body: RemixRequest) async throws -> RemixResult {
        try await post("api/remix", body: body, as: RemixResult.self)
    }

    /// Upload one photo (shrunk to a 1024px JPEG first). kind = "recipe" or "pantry".
    static func photo<T: Decodable>(_ image: UIImage, kind: String, as type: T.Type) async throws -> T {
        let jpeg = image.shrunk(maxEdge: 1024).jpegData(compressionQuality: 0.85) ?? Data()
        let boundary = "leafit-\(UUID().uuidString)"
        var body = Data()
        func field(_ s: String) { body.append(s.data(using: .utf8)!) }
        field("--\(boundary)\r\nContent-Disposition: form-data; name=\"kind\"\r\n\r\n\(kind)\r\n")
        field("--\(boundary)\r\nContent-Disposition: form-data; name=\"file\"; filename=\"photo.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n")
        body.append(jpeg)
        field("\r\n--\(boundary)--\r\n")
        var req = URLRequest(url: baseURL.appendingPathComponent("api/parse/photo"))
        req.httpMethod = "POST"
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        req.httpBody = body
        req.timeoutInterval = 90
        return try await send(req, as: type)
    }
}

extension UIImage {
    func shrunk(maxEdge: CGFloat) -> UIImage {
        let scale = min(1, maxEdge / max(size.width, size.height))
        guard scale < 1 else { return self }
        let target = CGSize(width: size.width * scale, height: size.height * scale)
        return UIGraphicsImageRenderer(size: target).image { _ in draw(in: CGRect(origin: .zero, size: target)) }
    }
}

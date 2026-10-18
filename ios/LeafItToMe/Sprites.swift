import SwiftUI

// Pixel-art sprites (same drawings as static/sprites.js). Each letter is a colour; "." is empty.
enum Sprites {
    static let palette: [Character: UInt32] = [
        "k": 0x2b2433, "g": 0x5cc97b, "G": 0x2f8f52, "l": 0xb8f0a8,
        "y": 0xffd65a, "o": 0xf6923a, "r": 0xef5d5d, "b": 0xb8743f, "B": 0x7a4a26,
        "w": 0xfffaf0, "s": 0xc9c1d6, "p": 0xff9ecb, "u": 0x7fcff7, "U": 0x3d86d6,
    ]

    static let art: [String: [String]] = [
        "sprout": [
            "................", "...kkk....kkk...", "..kllk...kgggk..", ".klllk..kggggk..",
            ".kllllk.kgggk...", "..kllllkkggk....", "...klllkgkk.....", "....kkkkgk......",
            ".......kgk......", ".......kgk......", ".......kgk......", "....kkkkkkkk....",
            "...kbbbbbbbbk...", "...kBbbbbbbBk...", "....kBBBBBBk....", ".....kkkkkk.....",
        ],
        "curry": [
            "................", "....s...s...s...", ".....s...s...s..", "....s...s...s...",
            "................", ".kkkkkkkkkkkkkk.", "kwwwwwooooogoook", "kwwwwooroooooook",
            ".kkkkkkkkkkkkkk.", ".kuuuuuuuuuuuuk.", "..kuuuuuuuuuuk..", "...kkkkkkkkkk...",
            "....kUUUUUUk....", "....kkkkkkkk....", "................", "................",
        ],
        "taco": [
            "................", "................", "................", "......kkkk......",
            "....kkgrglkk....", "...kgrlgrglgk...", "..kyklgrbbrgyk..", ".kyyybbbbbbbyyk.",
            ".kyyyyyyyyyyyyk.", "kyyyyyyyyyyyyyyk", "kyyyyyyyyyyyyyyk", ".kkkkkkkkkkkkkk.",
            "................", "................", "................", "................",
        ],
        "pasta": [
            "................", "................", "......kkkk......", "....kkrrrrkk....",
            "...kyyrrrryyk...", "..kyyyyrryyyyk..", "..kyyyyyyyygyk..", ".kkkkkkkkkkkkkk.",
            "kwwwwwwwwwwwwwwk", ".kwwwwwwwwwwwwk.", "..kkkkkkkkkkkk..", "................",
            "................", "................", "................", "................",
        ],
        "bowl": [
            "..............B.", ".............B..", "............B...", "...........B....",
            "..........B.....", ".kkkkkkkkkkkkkk.", "krwwrwwrrwwrwwrk", "krrwwrrwwrrwwrrk",
            ".kkkkkkkkkkkkkk.", ".kwuwuwuwuwuwuk.", "..kwwwwwwwwwwk..", "...kkkkkkkkkk...",
            "....kssssssk....", "....kkkkkkkk....", "................", "................",
        ],
        "can": [
            "................", "....kkkkkkkk....", "...kssssssssk...", "...kkkkkkkkkk...",
            "...kggggggggk...", "...kgwwwwwwgk...", "...kgwyyyywgk...", "...kgwyyyywgk...",
            "...kgwwwwwwgk...", "...kggggggggk...", "...kkkkkkkkkk...", "...kssssssssk...",
            "....kkkkkkkk....", "................", "................", "................",
        ],
        "camera": [
            "................", "................", "................", "......kkkk......",
            "..kkkkkuukkkkk..", ".kppppkkkkppwpk.", ".kppkkuuuukkppk.", ".kppkuuwuuukppk.",
            ".kppkuuuuuukppk.", ".kppkkuuuukkppk.", ".kppppkkkkppppk.", ".kkkkkkkkkkkkkk.",
            "................", "................", "................", "................",
        ],
    ]

    static let sampleSprite = ["butter_chicken": "curry", "beef_tacos": "taco", "bolognese": "pasta", "mapo_tofu": "bowl"]
}

struct PixelSprite: View {
    let name: String
    var size: CGFloat = 36

    var body: some View {
        let rows = Sprites.art[name] ?? []
        let w = rows.first?.count ?? 1
        let h = rows.count
        Canvas { ctx, canvas in
            let px = canvas.width / CGFloat(w)
            for (y, row) in rows.enumerated() {
                for (x, ch) in row.enumerated() where ch != "." {
                    guard let hex = Sprites.palette[ch] else { continue }
                    // tiny overlap avoids hairline gaps between pixels
                    ctx.fill(Path(CGRect(x: CGFloat(x) * px, y: CGFloat(y) * px, width: px + 0.5, height: px + 0.5)),
                             with: .color(Color(hex: hex)))
                }
            }
        }
        .frame(width: size, height: size * CGFloat(h) / CGFloat(w))
        .accessibilityHidden(true)
    }
}

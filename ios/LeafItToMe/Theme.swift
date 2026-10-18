import SwiftUI

// Same palette as the web app's retro theme.
extension Color {
    init(hex: UInt32) {
        self.init(red: Double((hex >> 16) & 0xff) / 255, green: Double((hex >> 8) & 0xff) / 255, blue: Double(hex & 0xff) / 255)
    }
    static let bg = Color(hex: 0xfff1dc)
    static let card = Color(hex: 0xfffaf0)
    static let ink = Color(hex: 0x2b2433)
    static let muted = Color(hex: 0x74697f)
    static let leaf = Color(hex: 0x5cc97b)
    static let mint = Color(hex: 0xb8f0a8)
    static let greenSoft = Color(hex: 0xd6f5cc)
    static let green = Color(hex: 0x2f8f52)
    static let coral = Color(hex: 0xf0624f)
    static let coralSoft = Color(hex: 0xffe0da)
    static let amber = Color(hex: 0xe8960f)
    static let amberSoft = Color(hex: 0xfff0c4)
    static let sky = Color(hex: 0x7fcff7)
    static let pink = Color(hex: 0xff9ecb)
    static let pinkSoft = Color(hex: 0xffe3f0)
    static let beige = Color(hex: 0xd9cbb4)
    static let screen = Color(hex: 0x17141f)

    static func group(_ g: String) -> Color {
        switch g {
        case "protein": return Color(hex: 0x4b8fd8)
        case "dairy": return Color(hex: 0x2fb3a5)
        case "spice": return Color(hex: 0xd6a23c)
        case "vegetable": return Color(hex: 0x4fa35a)
        case "grain": return Color(hex: 0xa87442)
        case "sauce": return Color(hex: 0x8b62c9)
        case "fat": return Color(hex: 0xcf6a42)
        case "fruit": return Color(hex: 0xd35c8f)
        default: return .gray
        }
    }
}

extension Font {
    /// "Pixel" headings: chunky monospaced, the closest built-in match to a pixel font.
    static func pixel(_ size: CGFloat, _ weight: Font.Weight = .heavy) -> Font { .system(size: size, weight: weight, design: .monospaced) }
    /// Friendly rounded body text.
    static func body(_ size: CGFloat, _ weight: Font.Weight = .medium) -> Font { .system(size: size, weight: weight, design: .rounded) }
}

/// Sticker look: thick outline + hard offset shadow.
struct Sticker: ViewModifier {
    var fill: Color = .card
    var radius: CGFloat = 14
    var shadow: CGFloat = 4
    var line: CGFloat = 3
    func body(content: Content) -> some View {
        content
            .background(RoundedRectangle(cornerRadius: radius).fill(fill))
            .overlay(RoundedRectangle(cornerRadius: radius).stroke(Color.ink, lineWidth: line))
            .background(RoundedRectangle(cornerRadius: radius).fill(Color.ink).offset(x: shadow, y: shadow))
    }
}

extension View {
    func sticker(_ fill: Color = .card, radius: CGFloat = 14, shadow: CGFloat = 4, line: CGFloat = 3) -> some View {
        modifier(Sticker(fill: fill, radius: radius, shadow: shadow, line: line))
    }
}

/// Buttons that press down like real keys.
struct PressStyle: ButtonStyle {
    var fill: Color = .leaf
    var radius: CGFloat = 12
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .background(RoundedRectangle(cornerRadius: radius).fill(fill))
            .overlay(RoundedRectangle(cornerRadius: radius).stroke(Color.ink, lineWidth: 3))
            .background(RoundedRectangle(cornerRadius: radius).fill(Color.ink).offset(x: configuration.isPressed ? 0 : 3, y: configuration.isPressed ? 0 : 3))
            .offset(x: configuration.isPressed ? 3 : 0, y: configuration.isPressed ? 3 : 0)
            .animation(.easeOut(duration: 0.06), value: configuration.isPressed)
    }
}

/// Round numbered badge for each step.
struct StepNumber: View {
    let n: Int
    let color: Color
    var body: some View {
        Text("\(n)").font(.pixel(15)).foregroundStyle(Color.ink)
            .frame(width: 30, height: 30)
            .background(Circle().fill(color))
            .overlay(Circle().stroke(Color.ink, lineWidth: 2))
    }
}

/// Faint dot-grid background, like the web app.
struct DotGrid: View {
    var body: some View {
        Canvas { ctx, size in
            let step: CGFloat = 18
            for x in stride(from: 0, through: size.width, by: step) {
                for y in stride(from: 0, through: size.height, by: step) {
                    ctx.fill(Path(ellipseIn: CGRect(x: x, y: y, width: 2.2, height: 2.2)), with: .color(Color.ink.opacity(0.09)))
                }
            }
        }
        .background(Color.bg)
        .ignoresSafeArea()
    }
}

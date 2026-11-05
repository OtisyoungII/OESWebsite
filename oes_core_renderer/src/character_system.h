#pragma once

#include <algorithm>
#include <cmath>
#include <string_view>

namespace oes::character {

enum class AnimationState { idle, blink, focus, scan };
enum class View { front, three_quarter, side };

struct Pose {
    float hover_y{};
    float pitch{};
    float yaw{};
    float gaze_x{};
    float gaze_y{};
    float aperture{1.0f};
    float pupil_scale{1.0f};
    float lens_depth{};
    float scan{};
};

inline float smoothstep(float value) {
    value = (std::clamp)(value, 0.0f, 1.0f);
    return value * value * (3.0f - 2.0f * value);
}

inline AnimationState animation_state(std::wstring_view value) {
    if (value == L"blink") return AnimationState::blink;
    if (value == L"focus") return AnimationState::focus;
    if (value == L"scan") return AnimationState::scan;
    return AnimationState::idle;
}

inline View view(std::wstring_view value) {
    if (value == L"three-quarter") return View::three_quarter;
    if (value == L"side") return View::side;
    return View::front;
}

class AnimationController {
public:
    AnimationController(AnimationState state, bool reduced_motion)
        : state_(state), reduced_motion_(reduced_motion) {}

    Pose sample(double seconds) const {
        Pose pose;
        if (reduced_motion_) return pose;
        const float time = static_cast<float>(seconds);
        pose.hover_y = std::sin(time * .72f) * .035f;
        pose.pitch = std::sin(time * .31f) * .018f;
        pose.yaw = std::sin(time * .23f + .7f) * .035f;
        pose.gaze_x = std::sin(time * .41f) * .055f;
        pose.gaze_y = std::sin(time * .29f + 1.1f) * .035f;

        if (state_ == AnimationState::blink) {
            const float phase = std::fmod(time + 1.9f, 2.8f);
            const float close = phase < .22f ? smoothstep(phase / .22f) :
                (phase < .48f ? 1.0f - smoothstep((phase - .22f) / .26f) : 0.0f);
            pose.aperture = 1.0f - close * .88f;
        } else if (state_ == AnimationState::focus) {
            const float focus = .5f + .5f * std::sin(time * 1.35f);
            pose.pupil_scale = .82f + focus * .23f;
            pose.lens_depth = (focus - .5f) * .075f;
        } else if (state_ == AnimationState::scan) {
            const float phase = std::fmod(time, 3.5f);
            pose.scan = phase < 1.2f ? .5f + .5f * std::sin(phase / 1.2f * 6.2831853f) : .5f;
            pose.gaze_x = (pose.scan - .5f) * .22f;
            pose.gaze_y = phase < 1.2f ? std::sin(phase / 1.2f * 12.566371f) * .025f : 0;
        }
        return pose;
    }

    AnimationState state() const { return state_; }
    bool reduced_motion() const { return reduced_motion_; }

private:
    AnimationState state_;
    bool reduced_motion_;
};

struct ThemeDefinition {
    std::string_view id;
    std::string_view label;
    bool completed;
    bool accessory_enabled;
};

inline constexpr ThemeDefinition themes[] = {
    {"default", "Futuristic robotic eye", true, false},
    {"pirate-minimal", "Pirate eyepatch accessory", false, true},
    {"pirate-full", "Complete pirate costume", false, true},
};

inline const ThemeDefinition& default_theme() { return themes[0]; }

} // namespace oes::character

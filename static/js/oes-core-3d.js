/*
===============================================================================
FILE: static/js/oes-core-3d.js

PURPOSE:
    Renders the OES Core as a true interactive WebGL object using Three.js.

UPDATED:
    July 16, 2026

RESPONSIBILITIES:
    [x] True three-dimensional OES Core sphere
    [x] Dimensional iris and pupil
    [x] OES identity positioned inside the iris
    [x] Iris dilation and contraction
    [x] Curved WebGL eyelids
    [x] Natural top-and-bottom blinking
    [x] Remove the detached CSS eyelids
    [x] Pointer-aware camera parallax
    [x] Deliberate drag-to-spin interaction
    [x] Controlled drag momentum
    [x] Automatic return to the forward-facing position
    [x] Prevent unexplained idle flipping
    [x] Internal energy geometry
    [x] Spatial particles
    [x] True three-dimensional orbit rings
    [x] Orbiting energy nodes
    [x] Dynamic lighting and reflections
    [x] Breathing and activation reactions
    [x] Section-aware accent colors
    [x] Responsive rendering
    [x] Reduced-motion support
    [x] CSS fallback support
    [x] Off-screen rendering suspension

ARCHITECTURE:
    static/js/oes-core.js
        Controls awareness, messages, behavior, activation, and blink events.

    static/js/oes-core-3d.js
        Controls WebGL geometry, lighting, camera, iris, eyelids, particles,
        drag behavior, and visual depth.

EVENTS RECEIVED:
    oes:coreactivated
    oes:corestatechange
    oes:coreblink
    oes:sectionchange
    oes:interestchange

EVENTS DISPATCHED:
    oes:core3dready
    oes:core3dfallback
    oes:core3ddragstart
    oes:core3ddragend

DEPENDENCIES:
    static/js/three/three.module.js
    static/js/three/three.core.js

IMPORTANT RULES:
    [x] The main sphere must never rotate by itself
    [x] The sphere may rotate only through pointer attention or direct dragging
    [x] Direct dragging may reveal the rear of the sphere
    [x] The sphere must return to the nearest forward-facing position
    [x] Eyelids must remain attached to the WebGL sphere
    [x] The old DOM eyelids must never appear above the WebGL Core
    [x] The OES logo remains unchanged
    [x] The existing CSS Core remains available as a fallback
    [x] Missing optional DOM elements must not break the page
===============================================================================
*/

import * as THREE from "./three/three.module.js";

/* ==========================================================================
   CONFIGURATION
============================================================================ */

const CORE_3D_CONFIG = {
    maximumPixelRatio: 2,
    mobilePixelRatio: 1.35,

    desktopSphereSegments: 96,
    mobileSphereSegments: 56,

    cameraFieldOfView: 34,
    cameraZ: 5.35,

    canvasExpansion: 0.34,

    sphereRadius: 1.22,
    innerSphereRadius: 1.15,
    shellRadius: 1.27,

    irisRadius: 0.53,
    pupilRadius: 0.22,

    pointerRotationX: 0.13,
    pointerRotationY: 0.19,

    cameraParallaxX: 0.13,
    cameraParallaxY: 0.09,

    dragRotationSpeed: 0.0085,
    dragVelocityStrength: 0.0034,
    dragVelocityDamping: 0.925,

    returnDelay: 850,
    returnStrength: 0.047,
    returnDamping: 0.82,

    maximumVerticalDragRotation: 1.05,

    breathingSpeed: 0.00105,
    breathingStrength: 0.012,

    irisIdleScale: 1,
    irisFocusedScale: 1.065,
    irisActivationScale: 1.11,

    pupilMinimumScale: 0.72,
    pupilMaximumScale: 1.18,

    blinkMinimumDelay: 6000,
    blinkMaximumDelay: 11000,
    blinkCloseDuration: 135,
    blinkHoldDuration: 68,
    blinkOpenDuration: 175,
    doubleBlinkChance: 0.14,

    particleCountDesktop: 190,
    particleCountMobile: 82,

    orbitSpeedOuter: 0.00055,
    orbitSpeedMiddle: -0.00072,
    orbitSpeedInner: 0.00092,

    activationDuration: 1500,

    defaultPrimary: "#38bdf8",
    defaultSecondary: "#22c55e",
    defaultPurple: "#a855f7",

    logoTexturePath: "/static/images/oes-logo.svg"
};

/* ==========================================================================
   MODULE STATE
============================================================================ */

let initialized = false;
let running = false;
let visible = true;
let destroyed = false;

let reducedMotion = false;
let mobileLayout = false;

let stage = null;
let coreButton = null;
let surface = null;
let fallbackLogo = null;

let canvas = null;
let renderer = null;
let scene = null;
let camera = null;
let clock = null;

let coreGroup = null;
let sphereGroup = null;
let faceGroup = null;
let orbitGroup = null;
let particleGroup = null;
let lightingGroup = null;

let outerSphere = null;
let innerSphere = null;
let energySphere = null;
let glassShell = null;
let rimRing = null;

let irisOuter = null;
let irisMiddle = null;
let pupil = null;
let pupilGlow = null;
let logoPlane = null;

let upperEyelid = null;
let lowerEyelid = null;
let eyelidGroup = null;

let orbitOuter = null;
let orbitMiddle = null;
let orbitInner = null;

let particles = null;
let particleMaterial = null;

let ambientLight = null;
let frontLight = null;
let primaryLight = null;
let secondaryLight = null;
let backLight = null;
let movingLight = null;

let resizeObserver = null;
let visibilityObserver = null;
let animationFrameId = null;

let blinkTimer = null;
let blinkAnimationFrameId = null;
let returnTimer = null;

let pointerTargetX = 0;
let pointerTargetY = 0;
let pointerCurrentX = 0;
let pointerCurrentY = 0;

let externalRotationX = 0;
let externalRotationY = 0;

let userRotationX = 0;
let userRotationY = 0;

let userRotationVelocityX = 0;
let userRotationVelocityY = 0;

let returnRotationX = 0;
let returnRotationY = 0;

let isDragging = false;
let isReturning = false;
let isBlinking = false;
let isActivated = false;

let dragPointerId = null;
let dragPreviousX = 0;
let dragPreviousY = 0;
let dragPreviousTime = 0;

let targetScale = 1;
let currentScale = 1;

let targetGlow = 0.58;
let currentGlow = 0.58;

let targetOrbitSpeed = 1;
let currentOrbitSpeed = 1;

let targetIrisScale = 1;
let currentIrisScale = 1;

let targetPupilScale = 1;
let currentPupilScale = 1;

let blinkAmount = 0;

let activationStrength = 0;
let activationStartedAt = 0;

let currentPrimaryColor =
    new THREE.Color(
        CORE_3D_CONFIG.defaultPrimary
    );

let currentSecondaryColor =
    new THREE.Color(
        CORE_3D_CONFIG.defaultSecondary
    );

let currentPurpleColor =
    new THREE.Color(
        CORE_3D_CONFIG.defaultPurple
    );

let targetPrimaryColor =
    currentPrimaryColor.clone();

let targetSecondaryColor =
    currentSecondaryColor.clone();

/* ==========================================================================
   CAPABILITY DETECTION
============================================================================ */

function supportsWebGL() {
    try {
        const testCanvas =
            document.createElement("canvas");

        return Boolean(
            window.WebGLRenderingContext &&
            (
                testCanvas.getContext("webgl2") ||
                testCanvas.getContext("webgl")
            )
        );
    } catch {
        return false;
    }
}

function prefersReducedMotion() {
    return window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;
}

function detectMobileLayout() {
    return (
        window.innerWidth <= 760 ||
        navigator.maxTouchPoints > 1
    );
}

/* ==========================================================================
   GENERAL UTILITIES
============================================================================ */

function clamp(
    value,
    minimum,
    maximum
) {
    return Math.min(
        Math.max(
            value,
            minimum
        ),
        maximum
    );
}

function lerp(
    start,
    end,
    amount
) {
    return (
        start +
        (
            end -
            start
        ) *
        amount
    );
}

function easeInOutCubic(value) {
    return value < 0.5
        ? 4 * value * value * value
        : 1 -
            Math.pow(
                -2 * value + 2,
                3
            ) /
            2;
}

function randomBetween(
    minimum,
    maximum
) {
    return (
        minimum +
        Math.random() *
        (
            maximum -
            minimum
        )
    );
}

function normalizeAngle(angle) {
    let normalized =
        angle %
        (
            Math.PI *
            2
        );

    if (normalized > Math.PI) {
        normalized -=
            Math.PI *
            2;
    }

    if (normalized < -Math.PI) {
        normalized +=
            Math.PI *
            2;
    }

    return normalized;
}

function readNumberVariable(
    element,
    variableName,
    fallback
) {
    if (!element) {
        return fallback;
    }

    const value =
        window
            .getComputedStyle(element)
            .getPropertyValue(variableName)
            .trim();

    const parsed =
        Number.parseFloat(value);

    return Number.isFinite(parsed)
        ? parsed
        : fallback;
}

function readAngleVariable(
    element,
    variableName,
    fallback = 0
) {
    if (!element) {
        return fallback;
    }

    const value =
        window
            .getComputedStyle(element)
            .getPropertyValue(variableName)
            .trim();

    const parsed =
        Number.parseFloat(value);

    return Number.isFinite(parsed)
        ? THREE.MathUtils.degToRad(parsed)
        : fallback;
}

function readColorVariable(
    variableName,
    fallback
) {
    const value =
        window
            .getComputedStyle(
                document.documentElement
            )
            .getPropertyValue(variableName)
            .trim();

    try {
        return new THREE.Color(
            value ||
            fallback
        );
    } catch {
        return new THREE.Color(
            fallback
        );
    }
}

function clearTimer(timerId) {
    if (timerId) {
        window.clearTimeout(timerId);
    }
}

function dispatchCore3DEvent(
    name,
    detail = {}
) {
    document.dispatchEvent(
        new CustomEvent(
            name,
            {
                detail: {
                    initialized,
                    renderer:
                        stage?.dataset
                            .oesCoreRenderer ||
                        "none",
                    ...detail
                }
            }
        )
    );
}

function disposeMaterial(material) {
    if (!material) {
        return;
    }

    Object.values(material)
        .forEach(
            (property) => {
                if (
                    property &&
                    typeof property ===
                        "object" &&
                    typeof property.dispose ===
                        "function"
                ) {
                    property.dispose();
                }
            }
        );

    material.dispose?.();
}

function disposeObject(object) {
    object?.traverse?.(
        (child) => {
            child.geometry?.dispose?.();

            if (
                Array.isArray(
                    child.material
                )
            ) {
                child.material.forEach(
                    disposeMaterial
                );
            } else {
                disposeMaterial(
                    child.material
                );
            }
        }
    );
}

/* ==========================================================================
   REMOVE OLD DETACHED EYELIDS
============================================================================ */

function removeLegacyEyelids() {
    const selectors = [
        ".oes-core__eyelid",
        ".oes-core__eyelid--top",
        ".oes-core__eyelid--bottom",
        ".core-eyelid",
        ".core-eyelid--top",
        ".core-eyelid--bottom",
        "[data-core-eyelid]"
    ];

    document
        .querySelectorAll(
            selectors.join(",")
        )
        .forEach(
            (element) => {
                element.remove();
            }
        );

    const observer =
        new MutationObserver(
            () => {
                document
                    .querySelectorAll(
                        selectors.join(",")
                    )
                    .forEach(
                        (element) => {
                            element.remove();
                        }
                    );
            }
        );

    if (coreButton) {
        observer.observe(
            coreButton,
            {
                childList: true,
                subtree: true
            }
        );
    }
}

/* ==========================================================================
   CANVAS AND RENDERER
============================================================================ */

function createCanvas() {
    canvas =
        document.createElement(
            "canvas"
        );

    canvas.className =
        "oes-core-3d-canvas";

    canvas.setAttribute(
        "aria-hidden",
        "true"
    );

    canvas.dataset.oesCore3d = "";

    const expansion =
        CORE_3D_CONFIG.canvasExpansion *
        100;

    Object.assign(
        canvas.style,
        {
            position: "absolute",
            top: `-${expansion}%`,
            right: `-${expansion}%`,
            bottom: `-${expansion}%`,
            left: `-${expansion}%`,
            width:
                `${100 + expansion * 2}%`,
            height:
                `${100 + expansion * 2}%`,
            display: "block",
            pointerEvents: "none",
            zIndex: "12",
            overflow: "visible"
        }
    );

    coreButton.appendChild(
        canvas
    );
}

function createRenderer() {
    renderer =
        new THREE.WebGLRenderer({
            canvas,
            alpha: true,
            antialias: !mobileLayout,
            powerPreference:
                "high-performance",
            premultipliedAlpha: true
        });

    renderer.setClearColor(
        0x000000,
        0
    );

    renderer.outputColorSpace =
        THREE.SRGBColorSpace;

    renderer.toneMapping =
        THREE.ACESFilmicToneMapping;

    renderer.toneMappingExposure =
        1.16;

    renderer.setPixelRatio(
        Math.min(
            window.devicePixelRatio || 1,
            mobileLayout
                ? CORE_3D_CONFIG
                    .mobilePixelRatio
                : CORE_3D_CONFIG
                    .maximumPixelRatio
        )
    );
}

/* ==========================================================================
   SCENE AND CAMERA
============================================================================ */

function createScene() {
    scene =
        new THREE.Scene();

    clock =
        new THREE.Clock();

    camera =
        new THREE.PerspectiveCamera(
            CORE_3D_CONFIG
                .cameraFieldOfView,
            1,
            0.1,
            100
        );

    camera.position.set(
        0,
        0,
        CORE_3D_CONFIG.cameraZ
    );

    scene.add(camera);

    coreGroup =
        new THREE.Group();

    sphereGroup =
        new THREE.Group();

    faceGroup =
        new THREE.Group();

    orbitGroup =
        new THREE.Group();

    particleGroup =
        new THREE.Group();

    lightingGroup =
        new THREE.Group();

    sphereGroup.add(
        faceGroup
    );

    coreGroup.add(
        sphereGroup,
        orbitGroup,
        particleGroup
    );

    scene.add(
        coreGroup,
        lightingGroup
    );
}

/* ==========================================================================
   LIGHTING
============================================================================ */

function createLights() {
    ambientLight =
        new THREE.AmbientLight(
            0x8ec5ff,
            0.82
        );

    frontLight =
        new THREE.DirectionalLight(
            0xffffff,
            3.15
        );

    frontLight.position.set(
        -1.8,
        2.5,
        4.7
    );

    primaryLight =
        new THREE.PointLight(
            currentPrimaryColor,
            10,
            9,
            2
        );

    primaryLight.position.set(
        -2.4,
        1.65,
        2.8
    );

    secondaryLight =
        new THREE.PointLight(
            currentSecondaryColor,
            7.5,
            8,
            2
        );

    secondaryLight.position.set(
        2.35,
        -1.5,
        2.25
    );

    backLight =
        new THREE.PointLight(
            currentPurpleColor,
            8,
            8,
            2
        );

    backLight.position.set(
        0,
        0.4,
        -3.2
    );

    movingLight =
        new THREE.PointLight(
            currentPrimaryColor,
            4.5,
            7,
            2
        );

    movingLight.position.set(
        2.6,
        1.8,
        2.2
    );

    lightingGroup.add(
        primaryLight,
        secondaryLight,
        backLight,
        movingLight
    );

    scene.add(
        ambientLight,
        frontLight
    );
}

/* ==========================================================================
   MAIN SPHERE
============================================================================ */

function createCoreSphere() {
    const segments =
        mobileLayout
            ? CORE_3D_CONFIG
                .mobileSphereSegments
            : CORE_3D_CONFIG
                .desktopSphereSegments;

    const outerGeometry =
        new THREE.SphereGeometry(
            CORE_3D_CONFIG.sphereRadius,
            segments,
            segments
        );

    const outerMaterial =
        new THREE.MeshPhysicalMaterial({
            color: 0x061426,
            roughness: 0.2,
            metalness: 0.38,
            transmission: 0.18,
            thickness: 1.2,
            transparent: true,
            opacity: 0.96,
            clearcoat: 1,
            clearcoatRoughness: 0.075,
            iridescence: 0.22,
            iridescenceIOR: 1.35,
            reflectivity: 0.96,
            emissive:
                currentPrimaryColor.clone(),
            emissiveIntensity: 0.09
        });

    outerSphere =
        new THREE.Mesh(
            outerGeometry,
            outerMaterial
        );

    const innerGeometry =
        new THREE.SphereGeometry(
            CORE_3D_CONFIG
                .innerSphereRadius,
            segments,
            segments
        );

    const innerMaterial =
        new THREE.MeshPhysicalMaterial({
            color: 0x010713,
            roughness: 0.3,
            metalness: 0.26,
            transparent: true,
            opacity: 0.95,
            emissive:
                currentSecondaryColor.clone(),
            emissiveIntensity: 0.055
        });

    innerSphere =
        new THREE.Mesh(
            innerGeometry,
            innerMaterial
        );

    const energyGeometry =
        new THREE.IcosahedronGeometry(
            1.04,
            mobileLayout
                ? 3
                : 5
        );

    const energyMaterial =
        new THREE.MeshBasicMaterial({
            color:
                currentPrimaryColor.clone(),
            transparent: true,
            opacity: 0.095,
            wireframe: true,
            blending:
                THREE.AdditiveBlending,
            depthWrite: false
        });

    energySphere =
        new THREE.Mesh(
            energyGeometry,
            energyMaterial
        );

    energySphere.rotation.set(
        0.28,
        -0.24,
        0.08
    );

    sphereGroup.add(
        innerSphere,
        energySphere,
        outerSphere
    );
}

/* ==========================================================================
   GLASS SHELL AND RIM
============================================================================ */

function createGlassShell() {
    const segments =
        mobileLayout
            ? 48
            : 82;

    const geometry =
        new THREE.SphereGeometry(
            CORE_3D_CONFIG.shellRadius,
            segments,
            segments
        );

    const material =
        new THREE.MeshPhysicalMaterial({
            color: 0x9bdcff,
            roughness: 0.035,
            metalness: 0.04,
            transmission: 0.78,
            thickness: 0.92,
            transparent: true,
            opacity: 0.13,
            clearcoat: 1,
            clearcoatRoughness: 0,
            side: THREE.FrontSide,
            blending:
                THREE.AdditiveBlending,
            depthWrite: false
        });

    glassShell =
        new THREE.Mesh(
            geometry,
            material
        );

    sphereGroup.add(
        glassShell
    );
}

function createRimRing() {
    const geometry =
        new THREE.TorusGeometry(
            1.255,
            0.018,
            16,
            mobileLayout
                ? 96
                : 180
        );

    const material =
        new THREE.MeshBasicMaterial({
            color:
                currentPrimaryColor.clone(),
            transparent: true,
            opacity: 0.68,
            blending:
                THREE.AdditiveBlending,
            depthWrite: false
        });

    rimRing =
        new THREE.Mesh(
            geometry,
            material
        );

    rimRing.position.z =
        0.1;

    sphereGroup.add(
        rimRing
    );
}

/* ==========================================================================
   DIMENSIONAL IRIS AND PUPIL
============================================================================ */

function createIris() {
    const irisOuterGeometry =
        new THREE.SphereGeometry(
            CORE_3D_CONFIG.irisRadius,
            mobileLayout ? 48 : 72,
            mobileLayout ? 32 : 48
        );

    const irisOuterMaterial =
        new THREE.MeshPhysicalMaterial({
            color:
                currentPrimaryColor.clone(),
            roughness: 0.22,
            metalness: 0.28,
            transparent: true,
            opacity: 0.96,
            clearcoat: 0.9,
            clearcoatRoughness: 0.08,
            emissive:
                currentPrimaryColor.clone(),
            emissiveIntensity: 0.3
        });

    irisOuter =
        new THREE.Mesh(
            irisOuterGeometry,
            irisOuterMaterial
        );

    irisOuter.scale.set(
        1,
        1,
        0.18
    );

    irisOuter.position.z =
        1.105;

    const irisMiddleGeometry =
        new THREE.TorusGeometry(
            0.37,
            0.082,
            24,
            mobileLayout ? 96 : 160
        );

    const irisMiddleMaterial =
        new THREE.MeshPhysicalMaterial({
            color:
                currentSecondaryColor.clone(),
            roughness: 0.18,
            metalness: 0.38,
            transparent: true,
            opacity: 0.96,
            emissive:
                currentSecondaryColor.clone(),
            emissiveIntensity: 0.38
        });

    irisMiddle =
        new THREE.Mesh(
            irisMiddleGeometry,
            irisMiddleMaterial
        );

    irisMiddle.position.z =
        1.205;

    const pupilGeometry =
        new THREE.SphereGeometry(
            CORE_3D_CONFIG.pupilRadius,
            mobileLayout ? 40 : 64,
            mobileLayout ? 28 : 42
        );

    const pupilMaterial =
        new THREE.MeshPhysicalMaterial({
            color: 0x01030a,
            roughness: 0.12,
            metalness: 0.54,
            transparent: true,
            opacity: 0.99,
            clearcoat: 1,
            clearcoatRoughness: 0.02,
            emissive: 0x020617,
            emissiveIntensity: 0.22
        });

    pupil =
        new THREE.Mesh(
            pupilGeometry,
            pupilMaterial
        );

    pupil.scale.set(
        1,
        1,
        0.22
    );

    pupil.position.z =
        1.235;

    const pupilGlowGeometry =
        new THREE.RingGeometry(
            0.19,
            0.29,
            mobileLayout ? 64 : 120
        );

    const pupilGlowMaterial =
        new THREE.MeshBasicMaterial({
            color:
                currentPrimaryColor.clone(),
            transparent: true,
            opacity: 0.38,
            blending:
                THREE.AdditiveBlending,
            depthWrite: false,
            side: THREE.DoubleSide
        });

    pupilGlow =
        new THREE.Mesh(
            pupilGlowGeometry,
            pupilGlowMaterial
        );

    pupilGlow.position.z =
        1.275;

    faceGroup.add(
        irisOuter,
        irisMiddle,
        pupil,
        pupilGlow
    );
}

/* ==========================================================================
   OES IDENTITY INSIDE THE IRIS
============================================================================ */

function createLogoPlane() {
    const textureLoader =
        new THREE.TextureLoader();

    textureLoader.load(
        CORE_3D_CONFIG.logoTexturePath,

        (texture) => {
            if (
                destroyed ||
                !faceGroup
            ) {
                texture.dispose();
                return;
            }

            texture.colorSpace =
                THREE.SRGBColorSpace;

            texture.anisotropy =
                Math.min(
                    renderer.capabilities
                        .getMaxAnisotropy(),
                    8
                );

            const geometry =
                new THREE.PlaneGeometry(
                    0.39,
                    0.39
                );

            const material =
                new THREE.MeshBasicMaterial({
                    map: texture,
                    transparent: true,
                    alphaTest: 0.015,
                    depthWrite: false,
                    toneMapped: false,
                    side: THREE.DoubleSide
                });

            logoPlane =
                new THREE.Mesh(
                    geometry,
                    material
                );

            logoPlane.position.z =
                1.325;

            faceGroup.add(
                logoPlane
            );

            hideFallbackLogo();
        },

        undefined,

        () => {
            showFallbackLogo();
        }
    );
}

/* ==========================================================================
   CURVED WEBGL EYELIDS
============================================================================ */

function createEyelidMaterial() {
    return new THREE.MeshPhysicalMaterial({
        color: 0x020712,
        roughness: 0.24,
        metalness: 0.36,
        transparent: true,
        opacity: 0,
        clearcoat: 0.8,
        clearcoatRoughness: 0.1,
        emissive:
            currentPrimaryColor.clone(),
        emissiveIntensity: 0.035,
        side: THREE.DoubleSide,
        depthWrite: true
    });
}

function createEyelids() {
    eyelidGroup =
        new THREE.Group();

    const segments =
        mobileLayout
            ? 48
            : 80;

    const upperGeometry =
        new THREE.SphereGeometry(
            1.285,
            segments,
            Math.floor(
                segments / 2
            ),
            0,
            Math.PI * 2,
            0,
            Math.PI / 2
        );

    const lowerGeometry =
        new THREE.SphereGeometry(
            1.285,
            segments,
            Math.floor(
                segments / 2
            ),
            0,
            Math.PI * 2,
            Math.PI / 2,
            Math.PI / 2
        );

    upperEyelid =
        new THREE.Mesh(
            upperGeometry,
            createEyelidMaterial()
        );

    lowerEyelid =
        new THREE.Mesh(
            lowerGeometry,
            createEyelidMaterial()
        );

    /*
    Open state:
        The two spherical halves are rotated away from the visible iris.

    Closed state:
        Both halves rotate toward the center and form one continuous sphere.
    */

    upperEyelid.rotation.x =
        -Math.PI / 2;

    lowerEyelid.rotation.x =
        Math.PI / 2;

    upperEyelid.renderOrder = 30;
    lowerEyelid.renderOrder = 30;

    eyelidGroup.add(
        upperEyelid,
        lowerEyelid
    );

    sphereGroup.add(
        eyelidGroup
    );

    updateEyelidGeometry(0);
}

function updateEyelidGeometry(amount) {
    if (
        !upperEyelid ||
        !lowerEyelid
    ) {
        return;
    }

    const eased =
        easeInOutCubic(
            clamp(
                amount,
                0,
                1
            )
        );

    upperEyelid.rotation.x =
        lerp(
            -Math.PI / 2,
            0,
            eased
        );

    lowerEyelid.rotation.x =
        lerp(
            Math.PI / 2,
            0,
            eased
        );

    const opacity =
        clamp(
            eased * 1.18,
            0,
            0.995
        );

    upperEyelid.material.opacity =
        opacity;

    lowerEyelid.material.opacity =
        opacity;

    const irisCompression =
        lerp(
            1,
            0.05,
            eased
        );

    if (faceGroup) {
        faceGroup.scale.y =
            irisCompression;
    }
}

/* ==========================================================================
   BLINKING
============================================================================ */

function animateBlinkSegment(
    from,
    to,
    duration
) {
    return new Promise(
        (resolve) => {
            const startedAt =
                performance.now();

            function update(time) {
                if (
                    destroyed ||
                    !initialized
                ) {
                    resolve();
                    return;
                }

                const progress =
                    clamp(
                        (
                            time -
                            startedAt
                        ) /
                        Math.max(
                            duration,
                            1
                        ),
                        0,
                        1
                    );

                blinkAmount =
                    lerp(
                        from,
                        to,
                        easeInOutCubic(
                            progress
                        )
                    );

                updateEyelidGeometry(
                    blinkAmount
                );

                if (progress >= 1) {
                    resolve();
                    return;
                }

                blinkAnimationFrameId =
                    window.requestAnimationFrame(
                        update
                    );
            }

            blinkAnimationFrameId =
                window.requestAnimationFrame(
                    update
                );
        }
    );
}

async function performBlink({
    allowDoubleBlink = true
} = {}) {
    if (
        isBlinking ||
        destroyed ||
        reducedMotion ||
        !upperEyelid ||
        !lowerEyelid
    ) {
        return;
    }

    isBlinking = true;

    await animateBlinkSegment(
        0,
        1,
        CORE_3D_CONFIG
            .blinkCloseDuration
    );

    await new Promise(
        (resolve) => {
            window.setTimeout(
                resolve,
                CORE_3D_CONFIG
                    .blinkHoldDuration
            );
        }
    );

    await animateBlinkSegment(
        1,
        0,
        CORE_3D_CONFIG
            .blinkOpenDuration
    );

    isBlinking = false;

    if (
        allowDoubleBlink &&
        Math.random() <
            CORE_3D_CONFIG
                .doubleBlinkChance
    ) {
        window.setTimeout(
            () => {
                performBlink({
                    allowDoubleBlink: false
                });
            },
            150
        );
    }
}

function scheduleBlink() {
    clearTimer(blinkTimer);

    if (
        destroyed ||
        reducedMotion
    ) {
        return;
    }

    blinkTimer =
        window.setTimeout(
            async () => {
                await performBlink();
                scheduleBlink();
            },
            randomBetween(
                CORE_3D_CONFIG
                    .blinkMinimumDelay,
                CORE_3D_CONFIG
                    .blinkMaximumDelay
            )
        );
}

function handleCoreBlink(event) {
    const phase =
        event.detail?.phase;

    const isOpeningEvent =
        phase === "open" ||
        phase === "opened" ||
        event.detail?.closed === false;

    if (isOpeningEvent) {
        return;
    }

    performBlink({
        allowDoubleBlink: false
    });
}

/* ==========================================================================
   THREE-DIMENSIONAL ORBITS
============================================================================ */

function createOrbit(
    radius,
    tube,
    color,
    opacity
) {
    const geometry =
        new THREE.TorusGeometry(
            radius,
            tube,
            14,
            mobileLayout ? 96 : 180
        );

    const material =
        new THREE.MeshBasicMaterial({
            color,
            transparent: true,
            opacity,
            blending:
                THREE.AdditiveBlending,
            depthWrite: false
        });

    return new THREE.Mesh(
        geometry,
        material
    );
}

function addOrbitNode(
    orbit,
    color,
    angle,
    size = 0.037
) {
    const geometry =
        new THREE.SphereGeometry(
            size,
            18,
            18
        );

    const material =
        new THREE.MeshBasicMaterial({
            color,
            transparent: true,
            opacity: 0.96,
            blending:
                THREE.AdditiveBlending
        });

    const node =
        new THREE.Mesh(
            geometry,
            material
        );

    const radius =
        orbit.geometry.parameters
            .radius;

    node.position.set(
        Math.cos(angle) * radius,
        Math.sin(angle) * radius,
        0
    );

    orbit.add(node);
}

function createOrbits() {
    orbitOuter =
        createOrbit(
            1.72,
            0.009,
            currentPrimaryColor.clone(),
            0.44
        );

    orbitOuter.rotation.set(
        1.12,
        0.1,
        0.16
    );

    orbitMiddle =
        createOrbit(
            1.51,
            0.011,
            currentSecondaryColor.clone(),
            0.5
        );

    orbitMiddle.rotation.set(
        0.18,
        1.12,
        -0.32
    );

    orbitInner =
        createOrbit(
            1.37,
            0.008,
            currentPurpleColor.clone(),
            0.38
        );

    orbitInner.rotation.set(
        0.74,
        0.82,
        0.42
    );

    orbitGroup.add(
        orbitOuter,
        orbitMiddle,
        orbitInner
    );

    addOrbitNode(
        orbitOuter,
        currentPrimaryColor,
        0,
        0.043
    );

    addOrbitNode(
        orbitOuter,
        currentSecondaryColor,
        Math.PI,
        0.031
    );

    addOrbitNode(
        orbitMiddle,
        currentSecondaryColor,
        Math.PI * 0.5,
        0.038
    );

    addOrbitNode(
        orbitMiddle,
        currentPrimaryColor,
        Math.PI * 1.4,
        0.027
    );

    addOrbitNode(
        orbitInner,
        currentPurpleColor,
        Math.PI * 1.35,
        0.034
    );
}

/* ==========================================================================
   SPATIAL PARTICLES
============================================================================ */

function createParticles() {
    const count =
        mobileLayout
            ? CORE_3D_CONFIG
                .particleCountMobile
            : CORE_3D_CONFIG
                .particleCountDesktop;

    const positions =
        new Float32Array(
            count * 3
        );

    for (
        let index = 0;
        index < count;
        index += 1
    ) {
        const radius =
            1.46 +
            Math.random() *
            1.25;

        const theta =
            Math.random() *
            Math.PI *
            2;

        const phi =
            Math.acos(
                2 *
                Math.random() -
                1
            );

        positions[index * 3] =
            radius *
            Math.sin(phi) *
            Math.cos(theta);

        positions[index * 3 + 1] =
            radius *
            Math.sin(phi) *
            Math.sin(theta);

        positions[index * 3 + 2] =
            radius *
            Math.cos(phi);
    }

    const geometry =
        new THREE.BufferGeometry();

    geometry.setAttribute(
        "position",
        new THREE.BufferAttribute(
            positions,
            3
        )
    );

    particleMaterial =
        new THREE.PointsMaterial({
            color:
                currentPrimaryColor.clone(),
            size:
                mobileLayout
                    ? 0.018
                    : 0.024,
            transparent: true,
            opacity: 0.45,
            blending:
                THREE.AdditiveBlending,
            depthWrite: false,
            sizeAttenuation: true
        });

    particles =
        new THREE.Points(
            geometry,
            particleMaterial
        );

    particleGroup.add(
        particles
    );
}

/* ==========================================================================
   POINTER ATTENTION
============================================================================ */

function handlePointerMove(event) {
    if (
        !stage ||
        reducedMotion
    ) {
        return;
    }

    const rect =
        stage.getBoundingClientRect();

    const normalizedX =
        clamp(
            (
                event.clientX -
                rect.left
            ) /
            Math.max(
                rect.width,
                1
            ) *
            2 -
            1,
            -1,
            1
        );

    const normalizedY =
        clamp(
            (
                event.clientY -
                rect.top
            ) /
            Math.max(
                rect.height,
                1
            ) *
            2 -
            1,
            -1,
            1
        );

    pointerTargetX =
        normalizedX;

    pointerTargetY =
        normalizedY;
}

function handlePointerLeaveStage() {
    if (isDragging) {
        return;
    }

    pointerTargetX = 0;
    pointerTargetY = 0;
}

/* ==========================================================================
   DRAG-TO-SPIN INTERACTION
============================================================================ */

function handleCorePointerDown(event) {
    if (
        reducedMotion ||
        !coreButton
    ) {
        return;
    }

    isDragging = true;
    isReturning = false;

    dragPointerId =
        event.pointerId;

    dragPreviousX =
        event.clientX;

    dragPreviousY =
        event.clientY;

    dragPreviousTime =
        performance.now();

    userRotationVelocityX = 0;
    userRotationVelocityY = 0;

    clearTimer(returnTimer);

    coreButton.setPointerCapture?.(
        event.pointerId
    );

    coreButton.classList.add(
        "oes-core--webgl-dragging"
    );

    stage?.classList.add(
        "oes-core-stage--webgl-dragging"
    );

    dispatchCore3DEvent(
        "oes:core3ddragstart",
        {
            pointerId:
                event.pointerId
        }
    );
}

function handleCorePointerMove(event) {
    if (
        !isDragging ||
        event.pointerId !==
            dragPointerId
    ) {
        return;
    }

    const now =
        performance.now();

    const elapsed =
        Math.max(
            now -
            dragPreviousTime,
            1
        );

    const deltaX =
        event.clientX -
        dragPreviousX;

    const deltaY =
        event.clientY -
        dragPreviousY;

    const rotationDeltaY =
        deltaX *
        CORE_3D_CONFIG
            .dragRotationSpeed;

    const rotationDeltaX =
        deltaY *
        CORE_3D_CONFIG
            .dragRotationSpeed;

    userRotationY +=
        rotationDeltaY;

    userRotationX =
        clamp(
            userRotationX +
            rotationDeltaX,
            -CORE_3D_CONFIG
                .maximumVerticalDragRotation,
            CORE_3D_CONFIG
                .maximumVerticalDragRotation
        );

    userRotationVelocityY =
        (
            rotationDeltaY /
            elapsed
        ) *
        16.67 *
        CORE_3D_CONFIG
            .dragVelocityStrength *
        100;

    userRotationVelocityX =
        (
            rotationDeltaX /
            elapsed
        ) *
        16.67 *
        CORE_3D_CONFIG
            .dragVelocityStrength *
        100;

    dragPreviousX =
        event.clientX;

    dragPreviousY =
        event.clientY;

    dragPreviousTime = now;
}

function beginReturnToFront() {
    if (
        isDragging ||
        destroyed
    ) {
        return;
    }

    returnRotationX = 0;

    /*
    normalizeAngle chooses the nearest equivalent forward position.

    A rotation of:
        2π
        -2π
        4π

    is visually identical to zero, so the Core returns by the shortest route.
    */

    returnRotationY =
        userRotationY -
        normalizeAngle(
            userRotationY
        );

    isReturning = true;
}

function scheduleReturnToFront() {
    clearTimer(returnTimer);

    returnTimer =
        window.setTimeout(
            beginReturnToFront,
            CORE_3D_CONFIG.returnDelay
        );
}

function handleCorePointerUp(event) {
    if (
        !isDragging ||
        event.pointerId !==
            dragPointerId
    ) {
        return;
    }

    isDragging = false;

    coreButton?.releasePointerCapture?.(
        event.pointerId
    );

    dragPointerId = null;

    coreButton?.classList.remove(
        "oes-core--webgl-dragging"
    );

    stage?.classList.remove(
        "oes-core-stage--webgl-dragging"
    );

    scheduleReturnToFront();

    dispatchCore3DEvent(
        "oes:core3ddragend",
        {
            rotation: {
                x: userRotationX,
                y: userRotationY
            }
        }
    );
}

function updateDragMomentum() {
    if (
        isDragging ||
        reducedMotion
    ) {
        return;
    }

    if (!isReturning) {
        userRotationY +=
            userRotationVelocityY;

        userRotationX =
            clamp(
                userRotationX +
                userRotationVelocityX,
                -CORE_3D_CONFIG
                    .maximumVerticalDragRotation,
                CORE_3D_CONFIG
                    .maximumVerticalDragRotation
            );

        userRotationVelocityY *=
            CORE_3D_CONFIG
                .dragVelocityDamping;

        userRotationVelocityX *=
            CORE_3D_CONFIG
                .dragVelocityDamping;

        if (
            Math.abs(
                userRotationVelocityY
            ) < 0.00008
        ) {
            userRotationVelocityY = 0;
        }

        if (
            Math.abs(
                userRotationVelocityX
            ) < 0.00008
        ) {
            userRotationVelocityX = 0;
        }

        return;
    }

    const deltaX =
        returnRotationX -
        userRotationX;

    const deltaY =
        returnRotationY -
        userRotationY;

    userRotationVelocityX =
        (
            userRotationVelocityX +
            deltaX *
            CORE_3D_CONFIG
                .returnStrength
        ) *
        CORE_3D_CONFIG
            .returnDamping;

    userRotationVelocityY =
        (
            userRotationVelocityY +
            deltaY *
            CORE_3D_CONFIG
                .returnStrength
        ) *
        CORE_3D_CONFIG
            .returnDamping;

    userRotationX +=
        userRotationVelocityX;

    userRotationY +=
        userRotationVelocityY;

    const finished =
        Math.abs(deltaX) < 0.0015 &&
        Math.abs(deltaY) < 0.0015 &&
        Math.abs(
            userRotationVelocityX
        ) < 0.001 &&
        Math.abs(
            userRotationVelocityY
        ) < 0.001;

    if (finished) {
        userRotationX = 0;
        userRotationY = 0;

        userRotationVelocityX = 0;
        userRotationVelocityY = 0;

        isReturning = false;
    }
}

/* ==========================================================================
   EXISTING OES SYSTEM INTEGRATION
============================================================================ */

function updateBehaviorInputs() {
    externalRotationX =
        readAngleVariable(
            stage,
            "--core-rotate-x",
            0
        );

    externalRotationY =
        readAngleVariable(
            stage,
            "--core-rotate-y",
            0
        );

    targetScale =
        readNumberVariable(
            stage,
            "--core-activation-scale",
            1
        );

    targetGlow =
        readNumberVariable(
            stage,
            "--core-glow-strength",
            0.58
        );

    targetOrbitSpeed =
        readNumberVariable(
            stage,
            "--core-orbit-speed",
            1
        );

    targetPrimaryColor =
        readColorVariable(
            "--awareness-primary",
            CORE_3D_CONFIG.defaultPrimary
        );

    targetSecondaryColor =
        readColorVariable(
            "--awareness-secondary",
            CORE_3D_CONFIG.defaultSecondary
        );

    const isFocused =
        stage?.classList.contains(
            "oes-core-stage--focused"
        ) ||
        stage?.classList.contains(
            "oes-core-stage--aware"
        );

    targetIrisScale =
        isActivated
            ? CORE_3D_CONFIG
                .irisActivationScale
            : isFocused
                ? CORE_3D_CONFIG
                    .irisFocusedScale
                : CORE_3D_CONFIG
                    .irisIdleScale;

    const pointerDistance =
        Math.min(
            Math.sqrt(
                pointerCurrentX *
                    pointerCurrentX +
                pointerCurrentY *
                    pointerCurrentY
            ),
            1
        );

    const dilation =
        lerp(
            CORE_3D_CONFIG
                .pupilMaximumScale,
            CORE_3D_CONFIG
                .pupilMinimumScale,
            pointerDistance
        );

    targetPupilScale =
        isActivated
            ? CORE_3D_CONFIG
                .pupilMaximumScale
            : dilation;
}

function handleCoreActivated() {
    isActivated = true;

    activationStrength = 1;

    activationStartedAt =
        performance.now();

    targetIrisScale =
        CORE_3D_CONFIG
            .irisActivationScale;

    targetPupilScale =
        CORE_3D_CONFIG
            .pupilMaximumScale;

    performBlink({
        allowDoubleBlink: false
    });

    window.setTimeout(
        () => {
            isActivated = false;
        },
        CORE_3D_CONFIG
            .activationDuration
    );
}

function handleCoreStateChange() {
    updateBehaviorInputs();
}

function handleVisibilityChange() {
    visible =
        document.visibilityState ===
        "visible";

    if (
        visible &&
        !running &&
        !reducedMotion
    ) {
        startRendering();
    }
}

/* ==========================================================================
   RESIZING
============================================================================ */

function resizeRenderer() {
    if (
        !canvas ||
        !renderer ||
        !camera
    ) {
        return;
    }

    const width =
        Math.max(
            canvas.clientWidth,
            1
        );

    const height =
        Math.max(
            canvas.clientHeight,
            1
        );

    renderer.setSize(
        width,
        height,
        false
    );

    camera.aspect =
        width / height;

    camera.updateProjectionMatrix();
}

/* ==========================================================================
   COLOR UPDATES
============================================================================ */

function updateColors() {
    currentPrimaryColor.lerp(
        targetPrimaryColor,
        0.042
    );

    currentSecondaryColor.lerp(
        targetSecondaryColor,
        0.042
    );

    primaryLight?.color.copy(
        currentPrimaryColor
    );

    movingLight?.color.copy(
        currentPrimaryColor
    );

    secondaryLight?.color.copy(
        currentSecondaryColor
    );

    outerSphere?.material
        .emissive.copy(
            currentPrimaryColor
        );

    innerSphere?.material
        .emissive.copy(
            currentSecondaryColor
        );

    energySphere?.material
        .color.copy(
            currentPrimaryColor
        );

    rimRing?.material
        .color.copy(
            currentPrimaryColor
        );

    irisOuter?.material
        .color.copy(
            currentPrimaryColor
        );

    irisOuter?.material
        .emissive.copy(
            currentPrimaryColor
        );

    irisMiddle?.material
        .color.copy(
            currentSecondaryColor
        );

    irisMiddle?.material
        .emissive.copy(
            currentSecondaryColor
        );

    pupilGlow?.material
        .color.copy(
            currentPrimaryColor
        );

    upperEyelid?.material
        .emissive.copy(
            currentPrimaryColor
        );

    lowerEyelid?.material
        .emissive.copy(
            currentPrimaryColor
        );

    orbitOuter?.material
        .color.copy(
            currentPrimaryColor
        );

    orbitMiddle?.material
        .color.copy(
            currentSecondaryColor
        );

    particleMaterial?.color.copy(
        currentPrimaryColor
    );
}

/* ==========================================================================
   ACTIVATION
============================================================================ */

function updateActivation(time) {
    if (
        activationStrength <= 0
    ) {
        return;
    }

    const progress =
        clamp(
            (
                time -
                activationStartedAt
            ) /
            CORE_3D_CONFIG
                .activationDuration,
            0,
            1
        );

    activationStrength =
        1 -
        progress;

    const pulse =
        Math.sin(
            progress *
            Math.PI
        );

    currentScale +=
        pulse *
        0.003;

    if (primaryLight) {
        primaryLight.intensity =
            lerp(
                10,
                19,
                activationStrength
            );
    }

    if (secondaryLight) {
        secondaryLight.intensity =
            lerp(
                7.5,
                14,
                activationStrength
            );
    }

    if (movingLight) {
        movingLight.intensity =
            lerp(
                4.5,
                11,
                activationStrength
            );
    }
}

/* ==========================================================================
   CAMERA, IRIS, LIGHTING, AND SPHERE MOTION
============================================================================ */

function updateCamera() {
    const targetCameraX =
        pointerCurrentX *
        CORE_3D_CONFIG
            .cameraParallaxX;

    const targetCameraY =
        -pointerCurrentY *
        CORE_3D_CONFIG
            .cameraParallaxY;

    camera.position.x =
        lerp(
            camera.position.x,
            targetCameraX,
            0.04
        );

    camera.position.y =
        lerp(
            camera.position.y,
            targetCameraY,
            0.04
        );

    camera.lookAt(
        0,
        0,
        0
    );
}

function updateIris(elapsed) {
    currentIrisScale =
        lerp(
            currentIrisScale,
            targetIrisScale,
            0.065
        );

    currentPupilScale =
        lerp(
            currentPupilScale,
            targetPupilScale,
            0.075
        );

    const tinyLifePulse =
        reducedMotion
            ? 1
            : (
                1 +
                Math.sin(
                    elapsed *
                    0.0017
                ) *
                0.008
            );

    irisOuter?.scale.set(
        currentIrisScale,
        currentIrisScale,
        0.18
    );

    irisMiddle?.scale.setScalar(
        currentIrisScale *
        tinyLifePulse
    );

    pupil?.scale.set(
        currentPupilScale,
        currentPupilScale,
        0.22
    );

    pupilGlow?.scale.setScalar(
        currentPupilScale *
        1.04
    );

    if (logoPlane) {
        logoPlane.scale.setScalar(
            lerp(
                0.94,
                1.05,
                currentPupilScale -
                    CORE_3D_CONFIG
                        .pupilMinimumScale
            )
        );
    }
}

function updateMovingLight(elapsed) {
    if (!movingLight) {
        return;
    }

    const radius =
        2.75;

    movingLight.position.x =
        Math.cos(
            elapsed *
            0.00036
        ) *
        radius;

    movingLight.position.y =
        1.2 +
        Math.sin(
            elapsed *
            0.00049
        ) *
        1.15;

    movingLight.position.z =
        2.1 +
        Math.sin(
            elapsed *
            0.00031
        ) *
        0.9;
}

function updateCoreMotion(
    elapsed,
    delta
) {
    pointerCurrentX =
        lerp(
            pointerCurrentX,
            pointerTargetX,
            0.052
        );

    pointerCurrentY =
        lerp(
            pointerCurrentY,
            pointerTargetY,
            0.052
        );

    currentScale =
        lerp(
            currentScale,
            targetScale,
            0.058
        );

    currentGlow =
        lerp(
            currentGlow,
            targetGlow,
            0.05
        );

    currentOrbitSpeed =
        lerp(
            currentOrbitSpeed,
            targetOrbitSpeed,
            0.04
        );

    updateDragMomentum();

    const breath =
        reducedMotion
            ? 1
            : (
                1 +
                Math.sin(
                    elapsed *
                    CORE_3D_CONFIG
                        .breathingSpeed
                ) *
                CORE_3D_CONFIG
                    .breathingStrength
            );

    coreGroup.scale.setScalar(
        currentScale *
        breath
    );

    const pointerRotationY =
        pointerCurrentX *
        CORE_3D_CONFIG
            .pointerRotationY;

    const pointerRotationX =
        -pointerCurrentY *
        CORE_3D_CONFIG
            .pointerRotationX;

    /*
    The main sphere does not rotate on its own.

    Rotation comes only from:
        existing OES attention movement
        pointer attention
        deliberate drag interaction
        controlled return-to-front motion
    */

    sphereGroup.rotation.x =
        externalRotationX +
        pointerRotationX +
        userRotationX;

    sphereGroup.rotation.y =
        externalRotationY +
        pointerRotationY +
        userRotationY;

    if (!reducedMotion) {
        energySphere.rotation.y -=
            0.00135 *
            delta *
            60;

        energySphere.rotation.z +=
            0.00082 *
            delta *
            60;

        particleGroup.rotation.y +=
            0.00024 *
            delta *
            60;

        particleGroup.rotation.x -=
            0.000085 *
            delta *
            60;
    }

    const lightResponse =
        clamp(
            currentGlow,
            0.2,
            1.25
        );

    outerSphere.material
        .emissiveIntensity =
        0.055 +
        lightResponse *
        0.16;

    innerSphere.material
        .emissiveIntensity =
        0.03 +
        lightResponse *
        0.095;

    energySphere.material.opacity =
        0.035 +
        lightResponse *
        0.12;

    glassShell.material.opacity =
        0.075 +
        lightResponse *
        0.095;

    rimRing.material.opacity =
        0.32 +
        lightResponse *
        0.46;

    irisOuter.material
        .emissiveIntensity =
        0.16 +
        lightResponse *
        0.33;

    irisMiddle.material
        .emissiveIntensity =
        0.2 +
        lightResponse *
        0.34;

    pupilGlow.material.opacity =
        0.18 +
        lightResponse *
        0.36;

    particleMaterial.opacity =
        0.18 +
        lightResponse *
        0.4;
}

/* ==========================================================================
   ORBIT MOTION
============================================================================ */

function updateOrbits(delta) {
    if (reducedMotion) {
        return;
    }

    const multiplier =
        currentOrbitSpeed *
        delta *
        60;

    orbitOuter.rotation.z +=
        CORE_3D_CONFIG
            .orbitSpeedOuter *
        multiplier;

    orbitOuter.rotation.y +=
        0.00018 *
        multiplier;

    orbitMiddle.rotation.z +=
        CORE_3D_CONFIG
            .orbitSpeedMiddle *
        multiplier;

    orbitMiddle.rotation.x -=
        0.00015 *
        multiplier;

    orbitInner.rotation.z +=
        CORE_3D_CONFIG
            .orbitSpeedInner *
        multiplier;

    orbitInner.rotation.y +=
        0.00024 *
        multiplier;
}

/* ==========================================================================
   RENDER LOOP
============================================================================ */

function renderFrame(time) {
    if (
        destroyed ||
        !running
    ) {
        return;
    }

    animationFrameId =
        window.requestAnimationFrame(
            renderFrame
        );

    if (
        !visible ||
        !scene ||
        !camera ||
        !renderer
    ) {
        return;
    }

    const delta =
        Math.min(
            clock.getDelta(),
            0.05
        );

    updateBehaviorInputs();
    updateColors();
    updateActivation(time);
    updateCoreMotion(time, delta);
    updateCamera();
    updateIris(time);
    updateMovingLight(time);
    updateOrbits(delta);

    renderer.render(
        scene,
        camera
    );
}

function startRendering() {
    if (
        running ||
        destroyed
    ) {
        return;
    }

    running = true;

    clock?.start();

    animationFrameId =
        window.requestAnimationFrame(
            renderFrame
        );
}

function stopRendering() {
    running = false;

    if (animationFrameId) {
        window.cancelAnimationFrame(
            animationFrameId
        );

        animationFrameId = null;
    }

    clock?.stop();
}

/* ==========================================================================
   OBSERVERS
============================================================================ */

function createObservers() {
    if (
        "ResizeObserver" in window
    ) {
        resizeObserver =
            new ResizeObserver(
                resizeRenderer
            );

        resizeObserver.observe(
            coreButton
        );
    }

    if (
        "IntersectionObserver" in window
    ) {
        visibilityObserver =
            new IntersectionObserver(
                (entries) => {
                    const entry =
                        entries[0];

                    visible =
                        Boolean(
                            entry?.isIntersecting
                        );

                    if (
                        visible &&
                        !running &&
                        !reducedMotion
                    ) {
                        startRendering();
                    }
                },
                {
                    threshold: 0.02
                }
            );

        visibilityObserver.observe(
            stage
        );
    }
}

/* ==========================================================================
   EVENT LISTENERS
============================================================================ */

function attachListeners() {
    window.addEventListener(
        "pointermove",
        handlePointerMove,
        {
            passive: true
        }
    );

    stage.addEventListener(
        "pointerleave",
        handlePointerLeaveStage,
        {
            passive: true
        }
    );

    coreButton.addEventListener(
        "pointerdown",
        handleCorePointerDown
    );

    coreButton.addEventListener(
        "pointermove",
        handleCorePointerMove
    );

    coreButton.addEventListener(
        "pointerup",
        handleCorePointerUp
    );

    coreButton.addEventListener(
        "pointercancel",
        handleCorePointerUp
    );

    coreButton.addEventListener(
        "lostpointercapture",
        (event) => {
            if (isDragging) {
                handleCorePointerUp(
                    event
                );
            }
        }
    );

    window.addEventListener(
        "resize",
        resizeRenderer,
        {
            passive: true
        }
    );

    document.addEventListener(
        "visibilitychange",
        handleVisibilityChange
    );

    document.addEventListener(
        "oes:coreactivated",
        handleCoreActivated
    );

    document.addEventListener(
        "oes:corestatechange",
        handleCoreStateChange
    );

    document.addEventListener(
        "oes:coreblink",
        handleCoreBlink
    );
}

function detachListeners() {
    window.removeEventListener(
        "pointermove",
        handlePointerMove
    );

    stage?.removeEventListener(
        "pointerleave",
        handlePointerLeaveStage
    );

    coreButton?.removeEventListener(
        "pointerdown",
        handleCorePointerDown
    );

    coreButton?.removeEventListener(
        "pointermove",
        handleCorePointerMove
    );

    coreButton?.removeEventListener(
        "pointerup",
        handleCorePointerUp
    );

    coreButton?.removeEventListener(
        "pointercancel",
        handleCorePointerUp
    );

    window.removeEventListener(
        "resize",
        resizeRenderer
    );

    document.removeEventListener(
        "visibilitychange",
        handleVisibilityChange
    );

    document.removeEventListener(
        "oes:coreactivated",
        handleCoreActivated
    );

    document.removeEventListener(
        "oes:corestatechange",
        handleCoreStateChange
    );

    document.removeEventListener(
        "oes:coreblink",
        handleCoreBlink
    );
}

/* ==========================================================================
   CSS AND FALLBACK PRESENTATION
============================================================================ */

function hideFallbackLogo() {
    if (!fallbackLogo) {
        return;
    }

    fallbackLogo.style.opacity =
        "0";

    fallbackLogo.style.visibility =
        "hidden";
}

function showFallbackLogo() {
    if (!fallbackLogo) {
        return;
    }

    fallbackLogo.style.opacity =
        "";

    fallbackLogo.style.visibility =
        "";
}

function hideLegacyCSSCoreLayers() {
    coreButton
        ?.querySelectorAll(
            [
                ".oes-core__energy",
                ".oes-core__shine",
                ".oes-core__pulse"
            ].join(",")
        )
        .forEach(
            (element) => {
                element.style.opacity =
                    "0";

                element.style.visibility =
                    "hidden";
            }
        );

    stage
        ?.querySelectorAll(
            ".core-orbit"
        )
        .forEach(
            (element) => {
                element.style.opacity =
                    "0";

                element.style.visibility =
                    "hidden";
            }
        );

    if (surface) {
        surface.style.opacity =
            "0";

        surface.style.visibility =
            "hidden";
    }
}

function restoreLegacyCSSCoreLayers() {
    coreButton
        ?.querySelectorAll(
            [
                ".oes-core__energy",
                ".oes-core__shine",
                ".oes-core__pulse"
            ].join(",")
        )
        .forEach(
            (element) => {
                element.style.opacity =
                    "";

                element.style.visibility =
                    "";
            }
        );

    stage
        ?.querySelectorAll(
            ".core-orbit"
        )
        .forEach(
            (element) => {
                element.style.opacity =
                    "";

                element.style.visibility =
                    "";
            }
        );

    if (surface) {
        surface.style.opacity =
            "";

        surface.style.visibility =
            "";
    }
}

function activateWebGLPresentation() {
    removeLegacyEyelids();
    hideLegacyCSSCoreLayers();
    hideFallbackLogo();

    stage.classList.add(
        "oes-core-stage--webgl"
    );

    coreButton.classList.add(
        "oes-core--webgl"
    );

    surface?.classList.add(
        "oes-core__surface--webgl"
    );

    stage.dataset.oesCoreRenderer =
        "webgl";

    delete stage.dataset
        .oesCoreFallback;
}

function activateFallback(reason) {
    restoreLegacyCSSCoreLayers();
    showFallbackLogo();

    stage?.classList.add(
        "oes-core-stage--webgl-fallback"
    );

    if (stage) {
        stage.dataset.oesCoreRenderer =
            "css";

        stage.dataset.oesCoreFallback =
            reason;
    }

    dispatchCore3DEvent(
        "oes:core3dfallback",
        {
            reason
        }
    );
}

/* ==========================================================================
   CLEANUP
============================================================================ */

export function destroyOESCore3D() {
    if (
        !initialized &&
        !renderer
    ) {
        return;
    }

    destroyed = true;

    stopRendering();
    detachListeners();

    clearTimer(blinkTimer);
    clearTimer(returnTimer);

    if (blinkAnimationFrameId) {
        window.cancelAnimationFrame(
            blinkAnimationFrameId
        );
    }

    resizeObserver?.disconnect();
    visibilityObserver?.disconnect();

    disposeObject(coreGroup);
    disposeObject(lightingGroup);

    renderer?.dispose();
    renderer?.forceContextLoss?.();

    canvas?.remove();

    restoreLegacyCSSCoreLayers();
    showFallbackLogo();

    stage?.classList.remove(
        "oes-core-stage--webgl",
        "oes-core-stage--webgl-dragging"
    );

    coreButton?.classList.remove(
        "oes-core--webgl",
        "oes-core--webgl-dragging"
    );

    surface?.classList.remove(
        "oes-core__surface--webgl"
    );

    initialized = false;
    running = false;
}

/* ==========================================================================
   PUBLIC STATE
============================================================================ */

export function getOESCore3DState() {
    return {
        initialized,
        running,
        visible,
        destroyed,
        reducedMotion,
        mobileLayout,
        isDragging,
        isReturning,
        isBlinking,
        isActivated,

        renderer:
            stage?.dataset
                .oesCoreRenderer ||
            "none",

        pointer: {
            x: pointerCurrentX,
            y: pointerCurrentY
        },

        rotation: {
            x: userRotationX,
            y: userRotationY
        },

        velocity: {
            x: userRotationVelocityX,
            y: userRotationVelocityY
        },

        iris: {
            scale: currentIrisScale,
            pupilScale:
                currentPupilScale
        },

        blinkAmount,

        glow: currentGlow,
        orbitSpeed:
            currentOrbitSpeed,
        scale: currentScale
    };
}

/* ==========================================================================
   INITIALIZATION
============================================================================ */

export function initializeOESCore3D() {
    if (
        initialized ||
        destroyed
    ) {
        return;
    }

    stage =
        document.querySelector(
            "[data-oes-core-stage]"
        );

    coreButton =
        document.querySelector(
            "[data-oes-core]"
        );

    surface =
        coreButton?.querySelector(
            ".oes-core__surface"
        );

    fallbackLogo =
        surface?.querySelector(
            "img"
        );

    if (
        !stage ||
        !coreButton ||
        !surface
    ) {
        return;
    }

    reducedMotion =
        prefersReducedMotion();

    mobileLayout =
        detectMobileLayout();

    removeLegacyEyelids();

    if (!supportsWebGL()) {
        activateFallback(
            "webgl-unavailable"
        );

        return;
    }

    try {
        createCanvas();
        createRenderer();
        createScene();
        createLights();

        createCoreSphere();
        createGlassShell();
        createRimRing();

        createIris();
        createLogoPlane();
        createEyelids();

        createOrbits();
        createParticles();

        resizeRenderer();
        createObservers();
        attachListeners();
        updateBehaviorInputs();

        activateWebGLPresentation();

        initialized = true;

        if (reducedMotion) {
            updateEyelidGeometry(0);

            renderer.render(
                scene,
                camera
            );
        } else {
            scheduleBlink();
            startRendering();
        }

        dispatchCore3DEvent(
            "oes:core3dready",
            {
                renderer: "webgl",
                mobileLayout,
                reducedMotion,
                features: [
                    "volumetric-sphere",
                    "dimensional-iris",
                    "pupil-dilation",
                    "webgl-eyelids",
                    "top-bottom-blink",
                    "drag-spin",
                    "drag-momentum",
                    "return-to-front",
                    "camera-parallax",
                    "spatial-particles",
                    "dynamic-lighting",
                    "three-dimensional-orbits"
                ]
            }
        );
    } catch (error) {
        console.error(
            "OES Core 3D initialization failed:",
            error
        );

        activateFallback(
            "initialization-error"
        );

        destroyOESCore3D();
    }
}
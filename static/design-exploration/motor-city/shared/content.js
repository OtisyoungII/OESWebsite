export const oesContent = Object.freeze({
  identity: {
    name: "Otis Execution Systems LLC",
    location: "Detroit, Michigan",
    tagline: "Ideas into execution.",
    heroEyebrow: "Detroit Built • Software • AI • Trading • Sports • Data",
    heroTitle: "We build technology that feels alive.",
    heroIntroduction: "Otis Execution Systems builds intelligent applications, trading and sports platforms, client software, connected data systems and practical technology people can actually use.",
    heroBelief: "Great technology should not belong only to giant corporations. Bring the business problem, community need, unfinished idea or ambitious dream. OES helps move it from imagination to execution."
  },
  products: [
    {
      id: "chaseingreen", name: "ChaseInGreen", category: "Trading Companion Platform", status: "Active TestFlight Testing",
      description: "ChaseInGreen is an OES-built trading companion undergoing production hardening and TestFlight testing. It brings market context, planning, risk tools, journaling and trader workspace features together without acting as a brokerage, exchange, wallet or financial institution.",
      features: ["Technical-analysis-driven dashboards and market state", "Position sizing, stop-loss and take-profit workflows", "Profit-protection and give-back planning tools", "Trade journaling, grouped P&L and account management", "Broker integrations, alerts and ongoing behavior analysis"],
      actions: [
        { label: "Test on TestFlight", href: "https://testflight.apple.com/join/nPjjyDSf" },
        { label: "Join ChaseInGreen Discord", href: "https://discord.gg/YjKFkdnj3" },
        { label: "ChaseInGreen Privacy Policy", href: "/privacy" }
      ],
      note: "Interested in testing advanced ChaseInGreen features? Selected testers can get early access to upcoming capabilities before release. Email info@otisexecutionsystems.com to learn more."
    },
    {
      id: "lottovate", name: "Lottovate", category: "Lottery Analytics", status: "Active TestFlight Testing",
      description: "Explore Michigan Daily 3 and Daily 4 results, compare historical patterns and keep personal picks organized in one iPhone app. No number or outcome is guaranteed.",
      features: ["Michigan Daily 3 and Daily 4 prediction lanes", "Result ingestion and historical-result handling", "Personal number tracking and Easy Picks", "Wager and winnings organization", "Expansion work for additional games, including Daily 5"],
      actions: [
        { label: "Test on TestFlight", href: "https://testflight.apple.com/join/CD35ByXj" },
        { label: "Join Lottovate Discord", href: "https://discord.gg/pf6sAYD33" }
      ]
    },
    {
      id: "sportfolio", name: "Sportfolio", category: "Multi-Sport Athlete Platform", status: "Active Field Testing",
      tagline: "Live sports. Verified stats. One athlete identity.",
      description: "Follow the story behind an athlete’s performance—from live game observations to source-aware stats and a lasting player record. Baseball is the first active field test.",
      features: ["Persistent athlete, team, league and season identity", "Mobile-first live scoring, lineups and pitch counts", "Independent team scoring and discrepancy review", "Verified officials, stat verification and audit history", "Media and future recruiting workflows"],
      actions: [{ label: "Try Sportfolio Web — URL Pending", disabled: true }, { label: "iOS TestFlight — Coming Soon", disabled: true }],
      note: "On Android? You can join Sportfolio testing through the web app while native mobile support continues to expand."
    },
    {
      id: "drinkswithfriendz", name: "Drinks With Friendz", category: "Client project developed by OES", status: "TestFlight Beta",
      description: "Find nearby places, explore them on a map and open the details needed to plan the next stop. OES developed this iPhone experience for the Drinks With Friendz client brand.",
      features: ["Native SwiftUI development", "Interactive maps and radius-based discovery", "Venue categories, photos, reviews and hours", "Calling, websites, sharing and directions", "TestFlight Beta"],
      actions: [
        { label: "Visit Website", href: "https://drinkswithfriendz.com/" },
        { label: "Test on TestFlight", href: "https://testflight.apple.com/join/mzknJ42e" },
        { label: "Drinks With Friendz Privacy", href: "/drinks-with-friendz/privacy" }
      ]
    }
  ],
  services: [
    ["Applied Artificial Intelligence", "Add focused AI to an application for analysis, prediction, recommendations, summarization, coaching, workflow support or decision assistance."],
    ["Native Mobile Applications", "Plan and build iPhone applications with SwiftUI, user flows, location services, cloud connections, testing and App Store preparation."],
    ["Web Platforms", "Build company websites, customer portals, dashboards, administrative tools and connected web applications that support real business operations."],
    ["Data and Analytics", "Organize raw information into reports, visual dashboards, behavior patterns, performance measurements and clearer decisions."],
    ["SaaS Product Development", "Build subscription products with accounts, service tiers, protected features and room to grow."],
    ["Workflow Automation", "Connect repetitive business processes, reduce manual steps, route information and create consistent digital workflows."],
    ["Product and Technology Consulting", "Turn an idea into a clear scope, realistic roadmap and practical plan for a working product."],
    ["AI, Digital Skills and IT Training", "Provide accessible technology instruction for employees, entrepreneurs, young people, community organizations and first-time AI users."]
  ],
  government: {
    status: "Active SAM.gov Registration", uei: "KGZSXZL6QRP6", cage: "22UC4",
    note: "Otis Execution Systems LLC maintains an active registration in the U.S. federal government’s System for Award Management and may pursue eligible federal contracting opportunities.",
    title: "Modern technology for real public needs.",
    paragraphs: [
      "Otis Execution Systems provides custom software, artificial intelligence, data analysis, workflow automation, digital training and prototype development for federal, state, municipal, nonprofit and community-focused work.",
      "OES focuses on clearly defined outcomes: helping people complete a process, giving staff better information, modernizing a manual workflow, testing a new idea or increasing access to useful technology."
    ],
    capabilities: [
      ["Custom Software Development", "Mobile apps, web systems, staff dashboards, public information tools and connected workflows built around a defined need."],
      ["AI and Data Systems", "Systems that organize information, identify patterns, support staff decisions and make complex data easier to understand."],
      ["Digital Platforms and Portals", "Secure service portals, account-based platforms, program dashboards and public-facing digital tools."],
      ["Technology and AI Training", "Practical instruction in artificial intelligence, prompting, software fundamentals, digital tools and responsible technology use."],
      ["Prototype and Technical Validation", "Turn an early concept into testable software, determine whether the workflow works for real users and identify what should improve before larger investment or rollout."],
      ["Federal, State and Local Support", "Technology services structured for public agencies, institutions, nonprofits, educational programs and community-serving organizations."]
    ]
  },
  community: [
    { type: "Technology education", name: "Apple Developer Academy", text: "OES grew through hands-on training in Swift, application development, product design, collaboration and building technology around real human needs.", links: [["Visit the Academy", "https://developeracademy.msu.edu/"], ["View Foundation programs", "https://developeracademy.msu.edu/foundation"]] },
    { type: "Detroit business ecosystem", name: "TechTown Detroit", text: "Founder programs, workshops, business resources and events connecting Detroit entrepreneurs with knowledge, support and opportunities to grow.", links: [["Visit TechTown", "https://techtowndetroit.org/"], ["View upcoming events", "https://techtowndetroit.org/events/"]] },
    { type: "Black technology ecosystem", name: "Black Tech Saturdays", text: "A Detroit-centered technology community creating access, education, visibility and stronger connections for Black builders, professionals, founders and future leaders.", links: [["Explore Black Tech Saturdays", "https://www.blacktechsaturdays.com/"]] },
    { type: "Community technology support", name: "Crossroads of Michigan", text: "OES supports community members with computer access, printing, resumes, digital assistance, AI exposure and practical help using technology.", links: [["Visit Crossroads", "https://www.crossroadsofmichigan.org/"]] },
    { type: "Technology, athletics and life preparation", name: "Coaching, Education and Mentorship", text: "OES combines AI education, digital skills, life preparation and athletic coaching to help young people recognize more pathways into high school, college and professional life.", detail: "Experience includes work with the Boys & Girls Club, Apple Developer Academy, community technology programs, Midwest baseball organizations and athletes pursuing serious baseball and football goals. Athletics can build discipline, create educational opportunities and make college more affordable. OES teaches both the game and the path beyond it." },
    { type: "OES belief", name: "Your idea belongs in the future.", text: "Whether it begins with a notebook, knitting needles, a classroom, a trading screen, a community problem or an unfinished dream, technology should help more people shape what comes next." }
  ],
  research: {
    title: "We explore before the path is obvious.",
    paragraphs: ["OES explores how software can respond more naturally, make difficult information clearer and help people decide what to do next."],
    lines: [
      ["ACTIVE", "Guidance that adapts to how people use a product"],
      ["ACTIVE", "Trading tools that bring market conditions, risk and past decisions together"],
      ["ACTIVE", "Pattern tools for financial and number-based applications"],
      ["TESTING", "Interfaces that move, focus and respond to attention"],
      ["EXPLORING", "Focused AI helpers for specific tasks inside an application"],
      ["FUTURE", "Voice, spatial and adaptive experiences for emerging devices"]
    ]
  },
  about: {
    title: "Building from Detroit with purpose, imagination and execution.",
    paragraphs: ["Otis Execution Systems LLC develops testable software products, client applications, trading and sports technology, backend APIs, integrations and connected data systems.", "OES combines artificial intelligence, mobile engineering, web development, data analysis, automation, product design, technical experimentation and community-centered education.", "We believe imperfections are not reasons to stop building. They are places where better systems, stronger people and new opportunities can begin."]
  },
  contact: {
    title: "Bring OES the idea.",
    text: "Tell us what you want to build, improve or finally get moving.",
    email: "info@otisexecutionsystems.com"
  }
});

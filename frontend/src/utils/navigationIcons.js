export const navigationIcons = {
  overview: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12.5 12 4l9 8.5"></path><path d="M6.5 10.5V20h11V10.5"></path></svg>`,
  users: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"></path><circle cx="9.5" cy="7.5" r="3.5"></circle><path d="M21 21v-2a4 4 0 0 0-3-3.87"></path><path d="M15 4.13a3.5 3.5 0 0 1 0 6.74"></path></svg>`,
  classes: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7.5 12 3l9 4.5-9 4.5Z"></path><path d="M7 10.5v4.5c0 1.66 2.24 3 5 3s5-1.34 5-3v-4.5"></path></svg>`,
  coursewares: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z"></path><path d="M14 3v5h5"></path><path d="M9 13h6"></path><path d="M9 17h6"></path></svg>`,
  assignments: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"></path><rect x="9" y="3" width="6" height="4" rx="1"></rect><path d="m9 14 2 2 4-5"></path></svg>`,
  evaluations: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20 5.5 23l1.5-7.5L2 10.8l7.8-.9L12 3l2.2 6.9 7.8.9-5 4.7 1.5 7.5Z"></path></svg>`,
  survey: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 11h9"></path><path d="M9 16h9"></path><path d="M9 6h9"></path><path d="m5 6 .5.5L7 5"></path><path d="m5 11 .5.5L7 10"></path><path d="m5 16 .5.5L7 15"></path></svg>`,
  discussions: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v10H8l-4 4Z"></path></svg>`,
  messages: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>`,
  rag: `<svg viewBox="0 0 24 24" aria-hidden="true"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M3 5v4c0 1.66 4.03 3 9 3s9-1.34 9-3V5"></path><path d="M3 9v4c0 1.66 4.03 3 9 3s9-1.34 9-3V9"></path><path d="M3 13v4c0 1.66 4.03 3 9 3s9-1.34 9-3v-4"></path></svg>`,
  quizzes: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.5 2H5a1 1 0 0 0-1 1v18a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V6l-4.5-4Z"></path><circle cx="12" cy="11" r="1.5"></circle><path d="M9 10.5c0-.55.6-1.2 1.5-1.5"></path><path d="M12 13c-1.2 0-2 .5-2 1"></path><path d="m15 2-4.5 4H15"></path></svg>`,
  notifications: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>`,
}

export function navigationIcon(id) {
  return navigationIcons[id] || navigationIcons.overview
}

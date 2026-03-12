import { Component } from "@angular/core";
import { bootstrapApplication } from "@angular/platform-browser";

@Component({
  selector: "app-root",
  standalone: true,
  template: `
    <main class="shell">
      <h1>CardDemo Modernization</h1>
      <p>Phase 0 frontend scaffold is ready for later feature slices.</p>
    </main>
  `,
  styles: [
    `
      .shell {
        display: grid;
        gap: 0.75rem;
        margin: 0 auto;
        max-width: 48rem;
        padding: 3rem 1.5rem;
      }
    `,
  ],
})
class ScaffoldRootComponent {}

void bootstrapApplication(ScaffoldRootComponent);

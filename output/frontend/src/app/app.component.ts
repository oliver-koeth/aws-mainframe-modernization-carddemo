import { Component } from "@angular/core";
import { RouterLink, RouterLinkActive, RouterOutlet } from "@angular/router";

@Component({
  selector: "app-root",
  standalone: true,
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: "./app.component.html",
  styles: [
    `
      :host {
        display: block;
      }

      .shell {
        display: grid;
        gap: 0.75rem;
        margin: 0 auto;
        max-width: 48rem;
        padding: 3rem 1.5rem;
      }

      .eyebrow {
        color: #6a6f7a;
        font-size: 0.875rem;
        letter-spacing: 0.08em;
        margin: 0;
        text-transform: uppercase;
      }

      h1,
      p {
        margin: 0;
      }

      .shell-header {
        display: grid;
        gap: 1rem;
      }

      .nav-link {
        border: 1px solid #c9d2de;
        border-radius: 999px;
        color: #183153;
        justify-self: start;
        padding: 0.5rem 0.9rem;
        text-decoration: none;
      }

      .nav-link.active {
        background: #183153;
        border-color: #183153;
        color: #fff;
      }
    `,
  ],
})
export class AppComponent {}

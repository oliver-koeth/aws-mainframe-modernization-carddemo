import { Component } from "@angular/core";
import { RouterOutlet } from "@angular/router";

@Component({
  selector: "app-root",
  standalone: true,
  imports: [RouterOutlet],
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
    `,
  ],
})
export class AppComponent {}

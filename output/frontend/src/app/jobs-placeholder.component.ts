import { Component } from "@angular/core";

@Component({
  selector: "app-jobs-placeholder",
  standalone: true,
  template: `
    <section class="jobs-card" aria-labelledby="jobs-heading">
      <p class="label">Batch Admin Surface</p>
      <h2 id="jobs-heading">Jobs placeholder</h2>
      <p>
        This scaffold route reserves space for scheduled job monitoring and control in
        later modernization slices.
      </p>
    </section>
  `,
  styles: [
    `
      .jobs-card {
        background: #f5f7fa;
        border: 1px solid #d8dee8;
        border-radius: 1rem;
        padding: 1.5rem;
      }

      .label {
        color: #5b6470;
        font-size: 0.8rem;
        letter-spacing: 0.08em;
        margin: 0 0 0.5rem;
        text-transform: uppercase;
      }

      h2 {
        margin: 0 0 0.75rem;
      }

      p {
        margin: 0;
      }
    `,
  ],
})
export class JobsPlaceholderComponent {}

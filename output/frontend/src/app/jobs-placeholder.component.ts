import { AsyncPipe, NgIf } from "@angular/common";
import { Component, inject } from "@angular/core";
import { ApiClientService } from "./api-client.service";

@Component({
  selector: "app-jobs-placeholder",
  standalone: true,
  imports: [AsyncPipe, NgIf],
  template: `
    <section class="jobs-card" aria-labelledby="jobs-heading">
      <p class="label">Batch Admin Surface</p>
      <h2 id="jobs-heading">Jobs placeholder</h2>
      <p>
        This scaffold route reserves space for scheduled job monitoring and control in
        later modernization slices.
      </p>
      <div class="status-panel">
        <p class="status-label">Scaffold API</p>
        <p *ngIf="jobs$ | async as jobs">
          Connected to <code>/api/jobs</code>. Current placeholder records:
          <strong>{{ jobs.length }}</strong>
        </p>
      </div>
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

      .status-panel {
        border-top: 1px solid #d8dee8;
        margin-top: 1rem;
        padding-top: 1rem;
      }

      .status-label {
        color: #5b6470;
        font-size: 0.75rem;
        letter-spacing: 0.08em;
        margin-bottom: 0.35rem;
        text-transform: uppercase;
      }

      code {
        background: #e8edf3;
        border-radius: 0.25rem;
        padding: 0.1rem 0.35rem;
      }
    `,
  ],
})
export class JobsPlaceholderComponent {
  private readonly apiClient = inject(ApiClientService);

  protected readonly jobs$ = this.apiClient.listJobs();
}

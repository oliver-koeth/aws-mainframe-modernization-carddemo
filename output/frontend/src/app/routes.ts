import { Routes } from "@angular/router";
import { JobsPlaceholderComponent } from "./jobs-placeholder.component";

export const routes: Routes = [
  {
    path: "",
    pathMatch: "full",
    redirectTo: "jobs",
  },
  {
    path: "jobs",
    component: JobsPlaceholderComponent,
  },
];

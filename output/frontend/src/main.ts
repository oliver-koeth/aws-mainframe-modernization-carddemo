import { provideHttpClient } from "@angular/common/http";
import { provideRouter } from "@angular/router";
import { bootstrapApplication } from "@angular/platform-browser";

import { AppComponent } from "./app/app.component";
import { routes } from "./app/routes";

void bootstrapApplication(AppComponent, {
  providers: [provideHttpClient(), provideRouter(routes)],
});

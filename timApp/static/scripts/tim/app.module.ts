import {BrowserModule} from "@angular/platform-browser";
import {ApplicationRef, DoBootstrap, NgModule} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {HeaderComponent} from "tim/header/header.component";
import {HTTP_INTERCEPTORS, HttpClientModule} from "@angular/common/http";
import {CreateItemComponent} from "tim/item/create-item.component";
import {ErrorStateDirective} from "tim/ui/error-state.directive";
import {ShortNameDirective} from "tim/ui/short-name.directive";
import {LocationDirective} from "tim/ui/location.directive";
import {TimUtilityModule} from "tim/ui/tim-utility.module";
import {TimeStampToMomentConverter} from "tim/util/time-stamp-to-moment-converter.service";
import {AnnotationComponent} from "tim/velp/annotation.component";
import {SignatureComponent} from "tim/ui/signature.component";
import {VelpSummaryComponent} from "tim/velp/velp-summary.component";
import {FooterComponent} from "tim/footer.component";
import {UserMenuComponent} from "tim/user/user-menu.component";
import {NoopAnimationsModule} from "@angular/platform-browser/animations";
import {LogoComponent} from "tim/ui/logo.component";
import {BsDropdownModule} from "ngx-bootstrap/dropdown";
import {setTheme} from "ngx-bootstrap/utils";
import {LoginMenuComponent} from "tim/user/login-menu.component";
import {FrontPageComponent} from "tim/frontpage/front-page.component";
import {BookmarkFolderBoxComponent} from "tim/bookmark/bookmark-folder-box.component";
import {SiteHeaderComponent} from "tim/header/site-header.component";
import {SearchBoxComponent} from "tim/search/search-box.component";
import {TypeaheadModule} from "ngx-bootstrap/typeahead";
import {SettingsComponent} from "tim/user/settings.component";
import {TooltipModule} from "ngx-bootstrap/tooltip";
import {LanguageSelectorComponent} from "tim/user/language-selector.component";
import {AccessCountdownComponent} from "tim/item/access-countdown.component";
import {SideBarMenuModule} from "tim/sidebarmenu/side-bar-menu.module";
import {DirectoryListComponent} from "tim/folder/directory-list.component";
import {TabsModule} from "ngx-bootstrap/tabs";
import {TemplateListComponent} from "tim/document/editing/template-list.component";
import {ConsentChoiceComponent} from "tim/ui/consent-choice.component";
import {ViewRangeNavigationComponent} from "tim/document/view-range-navigation.component";
import {HelpParContent} from "tim/document/editing/help-par-content.component";

@NgModule({
    declarations: [
        CreateItemComponent,
        ErrorStateDirective,
        HeaderComponent,
        LocationDirective,
        ShortNameDirective,
        AnnotationComponent,
        SignatureComponent,
        VelpSummaryComponent,
        FooterComponent,
        UserMenuComponent,
        LogoComponent,
        LoginMenuComponent,
        FrontPageComponent,
        BookmarkFolderBoxComponent,
        SiteHeaderComponent,
        SearchBoxComponent,
        SettingsComponent,
        LanguageSelectorComponent,
        AccessCountdownComponent,
        DirectoryListComponent,
        TemplateListComponent,
        ConsentChoiceComponent,
        ViewRangeNavigationComponent,
        HelpParContent,
    ],
    imports: [
        BrowserModule,
        HttpClientModule,
        FormsModule,
        TimUtilityModule,
        NoopAnimationsModule,
        SideBarMenuModule,
        BsDropdownModule.forRoot(),
        TypeaheadModule.forRoot(),
        TooltipModule.forRoot(),
        TabsModule.forRoot(),
    ],
    providers: [
        {
            provide: HTTP_INTERCEPTORS,
            useClass: TimeStampToMomentConverter,
            multi: true,
        },
    ],
})
export class AppModule implements DoBootstrap {
    ngDoBootstrap(appRef: ApplicationRef) {
        setTheme("bs3");
    }
}

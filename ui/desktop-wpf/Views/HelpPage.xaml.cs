using LibreOfficeAI.ViewModels;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Documents;

// To learn more about WinUI, the WinUI project structure,
// and more about our project templates, see: http://aka.ms/winui-project-info.

namespace LibreOfficeAI.Views
{
    /// <summary>
    /// An empty page that can be used on its own or navigated to within a Frame.
    /// </summary>
    public sealed partial class HelpPage : Page
    {
        public HelpViewModel ViewModel { get; }

        public HelpPage()
        {
            InitializeComponent();

            ViewModel = App.Services.GetRequiredService<HelpViewModel>();

            RootGrid.DataContext = ViewModel;

            ContentHost.ContentTemplate = (DataTemplate)Resources["HelpContentTemplate"];
        }

        private void NavLinksList_ItemClick(object sender, ItemClickEventArgs e)
        {
            var navLink = e.ClickedItem as NavLink;
            if (navLink?.Label == "Help")
                ContentHost.ContentTemplate = (DataTemplate)Resources["HelpContentTemplate"];
            else if (navLink?.Label == "About")
                ContentHost.ContentTemplate = (DataTemplate)Resources["AboutContentTemplate"];
        }

        private void OnLinkClick(Hyperlink sender, HyperlinkClickEventArgs e)
        {
            var uri = sender.NavigateUri;
            if (uri != null)
            {
                Windows.System.Launcher.LaunchUriAsync(uri);
            }
        }
    }
}

using System;
using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.UI.Xaml.Controls;

namespace LibreOfficeAI.ViewModels
{
    public partial class HelpViewModel
    {
        private ObservableCollection<NavLink> _navLinks = new ObservableCollection<NavLink>()
        {
            new NavLink() { Label = "Help", Symbol = Symbol.Help },
            new NavLink() { Label = "About", Symbol = Symbol.More },
        };

        public ObservableCollection<NavLink> NavLinks
        {
            get { return _navLinks; }
        }

        public event Action? OnRequestNavigateToMainPage;

        [RelayCommand]
        private void BackButton_Click()
        {
            OnRequestNavigateToMainPage?.Invoke();
        }
    }

    public class NavLink
    {
        public string Label { get; set; }
        public Symbol Symbol { get; set; }
    }
}

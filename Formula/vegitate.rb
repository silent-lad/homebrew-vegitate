class Vegitate < Formula
  include Language::Python::Virtualenv

  desc "Keep your Mac caffeinated while locking all keyboard and mouse input"
  homepage "https://github.com/silent-lad/homebrew-vegitate"
  url "https://github.com/silent-lad/homebrew-vegitate/archive/refs/tags/v0.1.3.tar.gz"
  sha256 "8456af974cfa42a9efc9bb40242b697277d33a1db2a2e87eb293dd61e609740c"
  license "MIT"
  head "https://github.com/silent-lad/homebrew-vegitate.git", branch: "main"

  depends_on :macos
  depends_on "python@3.13"

  resource "pyobjc-core" do
    url "https://files.pythonhosted.org/packages/f4/d2/29e5e536adc07bc3d33dd09f3f7cf844bf7b4981820dc2a91dd810f3c782/pyobjc_core-12.1-cp313-cp313-macosx_10_13_universal2.whl", using: :nounzip
    sha256 "01c0cf500596f03e21c23aef9b5f326b9fb1f8f118cf0d8b66749b6cf4cbb37a"
  end

  resource "pyobjc-framework-Cocoa" do
    url "https://files.pythonhosted.org/packages/ad/31/0c2e734165abb46215797bd830c4bdcb780b699854b15f2b6240515edcc6/pyobjc_framework_cocoa-12.1-cp313-cp313-macosx_10_13_universal2.whl", using: :nounzip
    sha256 "5a3dcd491cacc2f5a197142b3c556d8aafa3963011110102a093349017705118"
  end

  resource "pyobjc-framework-Quartz" do
    url "https://files.pythonhosted.org/packages/ba/2d/e8f495328101898c16c32ac10e7b14b08ff2c443a756a76fd1271915f097/pyobjc_framework_quartz-12.1-cp313-cp313-macosx_10_13_universal2.whl", using: :nounzip
    sha256 "629b7971b1b43a11617f1460cd218bd308dfea247cd4ee3842eb40ca6f588860"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/14/25/b208c5683343959b670dc001595f2f3737e051da617f66c31f7c4fa93abc/rich-14.3.3-py3-none-any.whl", using: :nounzip
    sha256 "793431c1f8619afa7d3b52b2cdec859562b950ea0d4b6b505397612db8d5362d"
  end

  resource "markdown-it-py" do
    url "https://files.pythonhosted.org/packages/94/54/e7d793b573f298e1c9013b8c4dade17d481164aa517d1d7148619c2cedbf/markdown_it_py-4.0.0-py3-none-any.whl", using: :nounzip
    sha256 "87327c59b172c5011896038353a81343b6754500a08cd7a4973bb48c6d578147"
  end

  resource "mdurl" do
    url "https://files.pythonhosted.org/packages/b3/38/89ba8ad64ae25be8de66a6d463314cf1eb366222074cfda9ee839c56a4b4/mdurl-0.1.2-py3-none-any.whl", using: :nounzip
    sha256 "84008a41e51615a49fc9966191ff91509e3c40b939176e643fd50a5c2196b8f8"
  end

  resource "Pygments" do
    url "https://files.pythonhosted.org/packages/c7/21/705964c7812476f378728bdf590ca4b771ec72385c533964653c68e86bdc/pygments-2.19.2-py3-none-any.whl", using: :nounzip
    sha256 "86540386c03d588bb81d44bc3928634ff26449851e99741617ecb9037ee5ec0b"
  end

  def install
    venv = virtualenv_create(libexec, "python3.13")

    # Install wheel resources directly (nounzip keeps .whl intact for pip)
    resources.each do |r|
      r.stage do
        venv.pip_install Dir["*.whl"]
      end
    end

    venv.pip_install_and_link buildpath
  end

  def caveats
    <<~EOS
      vegitate requires Accessibility permission to intercept input events.

      Grant access in:
        System Settings → Privacy & Security → Accessibility

      Toggle ON for your terminal app (Terminal, iTerm2, Warp, etc.)
    EOS
  end

  test do
    assert_match "vegitate", shell_output("#{bin}/vegitate --help")
    assert_match version.to_s, shell_output("#{bin}/vegitate --version")
  end
end

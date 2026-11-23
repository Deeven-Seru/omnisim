class Omnisim < Formula
  include Language::Python::Virtualenv

  desc "Universal Counterfactual Simulation Engine & Pre-Flight Action Gate"
  homepage "https://github.com/Deeven-Seru/omnisim"
  url "https://github.com/Deeven-Seru/omnisim/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "6a51d480c2661bb579fb48b8482d0d92866bb20f1b8ec2664d5b31518870f99c"
  license "MIT"
  head "https://github.com/Deeven-Seru/omnisim.git", branch: "main"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/omnisim", "simulate", "--domain", "systems", "--horizon", "4"
  end
end

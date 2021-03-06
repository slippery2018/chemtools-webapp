Functionality
-------------

### Molecules ###

All of the following forms of output are possible for all of the molecules generated.

- gjf - a standard Gaussian Cartesian connectivity molecule file
- mol2 - a standard Cartesian-style molecule file format
- png - this is just a very rough rendering of the structure of the molecule.
- svg - this is the same as the png rendering with the added benefit that it is a vector image
- json - this returns a json object with all of the properties of a molecule.
- Job - there also is a job form on each molecule page that will allow generation of job files for any of the clusters given a few parameters.

In addition to the files, the page for each structure also includes the exact name, the feature vector, and estimates for the HOMO, LUMO, and Excitation energies. These estimates are calculated using a support vector machines predictor which was trained on about 1100 single core benzobisazole structures with side lengths less than 5 aryl groups.

Currently the system implemented updates the predictors every night if there have been more structures added to the database.


### Jobs ###
#### Generating Job Files ####

Job files can be made on the respective molecule pages using the Job Form. The job form allows simple replacement for the mechanical task of making new job files for each molecule.

Added with just being able to view the job file there is Alpha functionality to be able to directly upload both jobs and molecules to a cluster and run the respective job. Currently, these submit at about a rate of half a molecule per second. The current assumption is that this is more network bound.

Jobs can also be made in bulk using the [Make Jobs](/chem/multi_job/) page.

#### Show Running Jobs ####

If you are logged in, and have set up your credentials, then under the [Running](/chem/jobs/) page you can see all the jobs you currently have running on any cluster you have credentials for. Along with seeing the currently running jobs, there are also buttons that allow you to kill running jobs.


### Upload ###
#### Log Parse ####

This takes normal Gaussian log files and will output a text file comma delimited with various useful values from the log file (Name, HOMO, LUMO, HomoOrbital, Dipole, Energy, Excited, Time).


#### Long Chain Limit ####

To calculate the long chain limit, a file formated like this is needed:

    # 1/n values
    0.09091, 0.04545, 0.0303, 0.02273
    # homo values
    -5.54384, -5.41377, -5.37377, -5.3686
    # lumo values
    -2.17367, -2.45232, -2.55599, -2.59491
    # gap values
    3.1548, 2.61, 2.4482, 2.3972

Where lines starting with "#" are comments. The `n` values can be given as either `n` or `1/n`. This will return a zipped file with a text file listing the fit parameters as well as two graphs plotting the HOMO/LUMO and the Gap values.

The actual reading of information can also be done now using just the log files. If you upload a set of log files with `n1, n2, ... nN` somewhere in the filename these logs will be put together. Once together they will be parsed for the relevant data and the long chain limit will be calculated. This simplifies the process by not requiring the creation of a separate file just for the data.

#### Structure View ####

A simple option to view the structure of a gjf or log file. This displays a simplfied png of the molecule for quickly viewing without needing a proper molecule renderer. This also supports multiple molecules at the same time.


#### Gjf Reset ####

This takes a log file and returns a gjf file with the extracted geometry. This is intended to be used to extract the optimized geometry from the DFT log files to then use as the TDDFT gjf file. _WARNING: this will not work in some cases where the job stopped part way through writing._ If this does occur, the parser will try to get the geometry from the top of the log file and return the same geometry that was used for the job.

In addition to just being able to write out the gjf with the same parameters that were used to generate the log file, this also allows the creation of TDDFT files. If you are logged in, you can use this same mechanism to then submit the TDDFT calculation on the spot.

#### Percent ####

This is a feature implemented just for benzobisazole molecules. It also requires that the calculations used must have included the `pop=full`, `pop=regu`, or any other calculation that ouputs the Molecular Orbital Coefficients block in gaussian. With those requirements met, this will compute the percent of the HOMO and LUMO orbitals that are on the horizontal and vertical axes. It will also display a simple view of the molecule to show what atoms were placed in which group.

### Users ###
#### Account ####

Chemtools-Webapp has a very simplified view of user accounts. They are mainly used as a shell to persistently store information like emails and usernames for submitting jobs on the clusters. They are also used as a way of keeping track of cluster credentials.

Registering an account is much like any other site. An email server is not set up yet so it does not do email verification, but that is more of a formality anyways. After registering, click the activation key link to active your account.

After your directories on the cluster are setup, then you need to setup your SSH Keys.


#### SSH Keys ####

SSH keys can be generated for direct access to the clusters, or you can provide your own. The ones being used are generated by PyCrypto and are 2048 bit keys.

For the initial setup of the SSH keys, it does require a little bit of foot work. Which amounts to SSH-ing into the cluster of choice and running the following command, where $USERNAME is your username.

    $ wget /u/$USERNAME/id_rsa.pub -O- >> ~/.ssh/authorized_keys

After this key is added nothing else will have to be done. If you change your ssh key with chemtools it will auto update all of the clusters that you have credentials for with the new key.


#### Credentials ####

To give chemtools the ability to get and submit files/jobs on the clusters it must have the correct credentials stored so that it can log in. Credentials come in two forms: credentials using passwords, and credentials using ssh keys. The former is less secure due to the fact that the login password must be stored on the chemtools server. In light of this, the passwords are all stored with 128 bit AES encryption. The latter type of credential makes use of the public/private keys that chemtools generates for each user. To use these, you will need to follow the instructions in the [SSH Keys](#ssh-keys) section.

It is _strongly_ recommended to use the SSH key type credential for clusters.

If you are logged in, Credentials can be added in the [account settings pages](/u/username/credentials/).



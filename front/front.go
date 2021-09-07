package main

import (
	_ "embed"
	"encoding/json"
	"html/template"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
)

const SEPARATOR = " ::: "

//go:embed template.html
var template_source string

type Connection struct {
	TE_group     string `json:"te_group"`
	Canvas_group string `json:"canvas_group"`
}

func (c Connection) String() string {
	return strings.Join([]string{c.TE_group, c.Canvas_group}, SEPARATOR)
}

type Data struct {
	TE_groups     []string
	Canvas_groups []int
	Connections   []Connection
}

func assert(cond bool) {
	if !cond {
		log.Fatal("Assertion failed")
	}
}

func get(url string, data interface{}) {
	resp, _ := http.Get(url)
	defer resp.Body.Close()
	jsonData, _ := io.ReadAll(resp.Body)
	json.Unmarshal(jsonData, data)
}

// Send a request with URL parameters and no body and disregard the result.
func request(method string, url string, params url.Values) {
	req, _ := http.NewRequest(method, url+"?"+params.Encode(), nil)
	http.DefaultClient.Do(req)
}

func main() {
	tmpl, err := template.New("main").Parse(template_source)
	if err != nil {
		log.Fatal(err)
	}

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		var data Data
		get(os.Getenv("TE_CANVAS_URL")+"/api/timeedit?number_of_objects=100", &data.TE_groups)
		get(os.Getenv("TE_CANVAS_URL")+"/api/canvas", &data.Canvas_groups)
		get(os.Getenv("TE_CANVAS_URL")+"/api/connection", &data.Connections)
		tmpl.Execute(w, data)
	})

	http.HandleFunc("/add", func(w http.ResponseWriter, r *http.Request) {
		r.ParseForm()
		var te_group, canvas_group string
		for k, _ := range r.Form {
			if k[:2] == "te" {
				te_group = k[3:]
			} else {
				assert(k[:2] == "ca")
				canvas_group = k[3:]
			}
		}

		request("POST", os.Getenv("TE_CANVAS_URL")+"/api/connection", url.Values{
			"te_group":     {te_group},
			"canvas_group": {canvas_group},
		})

		http.Redirect(w, r, "/", http.StatusFound)
	})

	http.HandleFunc("/delete", func(w http.ResponseWriter, r *http.Request) {
		r.ParseForm()
		var te_group, canvas_group string
		for k, _ := range r.Form {
			// NOTE: Quick hack here
			parts := strings.Split(k, SEPARATOR)
			te_group, canvas_group = parts[0], parts[1]

			request("DELETE", os.Getenv("TE_CANVAS_URL")+"/api/connection",
				url.Values{
					"te_group":     {te_group},
					"canvas_group": {canvas_group},
				})
		}

		http.Redirect(w, r, "/", http.StatusFound)
	})

	log.Fatal(http.ListenAndServe(":8080", nil))
}
